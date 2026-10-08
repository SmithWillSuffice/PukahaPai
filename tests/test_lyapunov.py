from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lyapunov import classify_lyapunov, summarize_lyapunov
from generate_julia_odesolver import generate_julia_code
from plots4model import main as build_html_report

try:
    import tomllib
except ModuleNotFoundError:
    import toml as _toml
    tomllib = None


MODEL_DIR = ROOT / "models"
TEMPLATE_DIR = ROOT / "templates"


def load_toml(path):
    if tomllib is None:
        return _toml.load(path)
    with open(path, "rb") as f:
        return tomllib.load(f)


def rk4_state_tangent_step(x, v, dt, rhs, jac):
    k1x = rhs(x)
    k1v = jac(x) @ v

    x2 = x + 0.5 * dt * k1x
    v2 = v + 0.5 * dt * k1v
    k2x = rhs(x2)
    k2v = jac(x2) @ v2

    x3 = x + 0.5 * dt * k2x
    v3 = v + 0.5 * dt * k2v
    k3x = rhs(x3)
    k3v = jac(x3) @ v3

    x4 = x + dt * k3x
    v4 = v + dt * k3v
    k4x = rhs(x4)
    k4v = jac(x4) @ v4

    x_new = x + (dt / 6.0) * (k1x + 2*k2x + 2*k3x + k4x)
    v_new = v + (dt / 6.0) * (k1v + 2*k2v + 2*k3v + k4v)
    return x_new, v_new


def reference_largest_lyapunov(rhs, jac, x0, dt, t1, transient, renormalize_dt):
    """Independent RK4/Benettin reference used only by these unit tests."""
    x = np.asarray(x0, dtype=float)
    v = np.ones_like(x)
    v /= np.linalg.norm(v)

    t = 0.0
    started = False
    elapsed = 0.0
    since = 0.0
    log_sum = 0.0
    estimates = []

    n_steps = int(round(t1 / dt))
    for _ in range(n_steps):
        if not started and t >= transient - 0.5*dt:
            v[:] = 1.0
            v /= np.linalg.norm(v)
            started = True

        x, v = rk4_state_tangent_step(x, v, dt, rhs, jac)
        t += dt

        if not started:
            # Tangent history before the configured transient is discarded.
            v[:] = 1.0
            v /= np.linalg.norm(v)
            continue

        elapsed += dt
        since += dt
        if since + 1e-12 >= renormalize_dt:
            stretch = np.linalg.norm(v)
            log_sum += np.log(stretch)
            v /= stretch
            estimates.append((t, log_sum / elapsed))
            since = 0.0

    return pd.DataFrame(estimates, columns=["t", "lambda_max"])


def pendulum_system(config):
    p = config["parameters"]
    d = p["damping"]
    g = p["g"]
    length = p["length"]

    def rhs(x):
        theta, omega = x
        return np.array([omega, -d*omega - (g/length)*np.sin(theta)])

    def jac(x):
        theta, _ = x
        return np.array([
            [0.0, 1.0],
            [-(g/length)*np.cos(theta), -d],
        ])

    return rhs, jac


def lorenz_system(config):
    p = config["parameters"]
    sigma, rho, beta = p["sigma"], p["rho"], p["beta"]

    def rhs(x):
        X, Y, Z = x
        return np.array([
            sigma*(Y-X),
            X*(rho-Z)-Y,
            X*Y-beta*Z,
        ])

    def jac(x):
        X, Y, Z = x
        return np.array([
            [-sigma, sigma, 0.0],
            [rho-Z, -1.0, -X],
            [Y, X, -beta],
        ])

    return rhs, jac


def model_reference_lyapunov(model_file):
    config = load_toml(MODEL_DIR / model_file)
    names = config["variables"]["names"]
    x0 = [config["initial_conditions"][name] for name in names]
    lyap = config["lyapunov"]
    dt = config["solver"]["dt"]
    t1 = config["tspan"]["t1"] - config["tspan"]["t0"]

    if model_file.startswith("pendulum"):
        rhs, jac = pendulum_system(config)
    else:
        rhs, jac = lorenz_system(config)

    return reference_largest_lyapunov(
        rhs, jac, x0,
        dt=dt,
        t1=t1,
        transient=lyap["transient"],
        renormalize_dt=lyap["renormalize_dt"],
    )


def test_pendulum_has_negative_largest_lyapunov_exponent():
    df = model_reference_lyapunov("pendulum.toml")
    summary = summarize_lyapunov(df)
    assert summary.tail_mean < -0.02
    assert classify_lyapunov(summary.tail_mean) == "contracting"


def test_standard_lorenz_attractor_has_positive_largest_lyapunov_exponent():
    df = model_reference_lyapunov("lorenz_attractor.toml")
    summary = summarize_lyapunov(df)
    # rho=28 is the standard chaotic regime; leave a generous lower bound so
    # the test checks the sign robustly rather than a literature calibration.
    assert summary.tail_mean > 0.2
    assert classify_lyapunov(summary.tail_mean) == "exponentially sensitive"


def test_lorenz_unstable_equilibrium_has_positive_largest_lyapunov_exponent():
    df = model_reference_lyapunov("lorenz_attractor_unstable.toml")
    summary = summarize_lyapunov(df)
    assert summary.tail_mean > 1.0
    assert classify_lyapunov(summary.tail_mean) == "exponentially sensitive"


def test_lyapunov_toml_controls_are_present():
    for name in (
        "pendulum.toml",
        "lorenz_attractor.toml",
        "lorenz_attractor_unstable.toml",
    ):
        config = load_toml(MODEL_DIR / name)
        lyap = config["lyapunov"]
        assert lyap["enabled"] is True
        assert lyap["renormalize_dt"] > 0.0
        assert lyap["transient"] >= 0.0


def test_generator_renders_lyapunov_support(tmp_path, monkeypatch):
    models = tmp_path / "models"
    models.mkdir()
    source = MODEL_DIR / "pendulum.toml"
    (models / source.name).write_text(source.read_text())

    template = (TEMPLATE_DIR / "ode_dae_solver_cmdl.jl.template").read_text()
    monkeypatch.chdir(tmp_path)
    generate_julia_code("pendulum", template, gui_version=False)

    generated = (models / "pendulum_cmdl.jl").read_text()
    assert 'pendulum_lyapunov.csv' in generated
    assert 'write(lyapunov_outfile, "t,lambda_max\\n")' in generated
    assert "compute_ode_jacobian" in generated
    assert "J_ode = -J_residual" in generated
    assert "exp(J * delta_t)" in generated
    assert "renormalize_dt=0.1" in generated
    assert "transient=20.0" in generated


def test_default_plot_layout_is_three_tabs():
    config = load_toml(MODEL_DIR / "lorenz_attractor.toml")
    assert config.get("plots", {}).get("combine_stability_lyapunov_plots", False) is False


def test_pendulum_explicitly_uses_default_separate_analysis_tabs():
    config = load_toml(MODEL_DIR / "pendulum.toml")
    assert config["plots"]["combine_stability_lyapunov_plots"] is False



def test_html_report_has_three_branded_tabs_by_default(tmp_path, monkeypatch):
    models = tmp_path / "models"
    models.mkdir()
    (models / "pendulum.toml").write_text((MODEL_DIR / "pendulum.toml").read_text())
    (models / "pendulum.csv").write_text(
        "t,theta,omega\n0.0,0.1,0.0\n0.1,0.09,-0.1\n"
    )
    (models / "pendulum_eigen.csv").write_text(
        "t,e1,e2\n0.0,-0.05+3.1im,-0.05-3.1im\n"
    )
    (models / "pendulum_lyapunov.csv").write_text(
        "t,lambda_max\n20.1,-0.04\n100.0,-0.05\n"
    )

    monkeypatch.chdir(tmp_path)
    build_html_report("pendulum")
    html = (models / "pendulum.html").read_text()

    assert ">Dynamics<" in html
    assert ">Stability<" in html
    assert ">Lyapunov<" in html
    assert "#1E90FF" in html
    assert "#70C1A3" in html
    assert "background: #000" in html


def test_combined_analysis_tab_is_toml_controlled(tmp_path, monkeypatch):
    models = tmp_path / "models"
    models.mkdir()
    text = (MODEL_DIR / "pendulum.toml").read_text().replace(
        "combine_stability_lyapunov_plots = false",
        "combine_stability_lyapunov_plots = true",
    )
    (models / "pendulum.toml").write_text(text)
    (models / "pendulum.csv").write_text(
        "t,theta,omega\n0.0,0.1,0.0\n0.1,0.09,-0.1\n"
    )
    (models / "pendulum_eigen.csv").write_text(
        "t,e1,e2\n0.0,-0.05+3.1im,-0.05-3.1im\n"
    )
    (models / "pendulum_lyapunov.csv").write_text(
        "t,lambda_max\n20.1,-0.04\n100.0,-0.05\n"
    )

    monkeypatch.chdir(tmp_path)
    build_html_report("pendulum")
    html = (models / "pendulum.html").read_text()

    assert "Stability &amp; Lyapunov" in html
    assert "showTab('analysis')" in html
    assert "showTab('stability')" not in html
    assert "showTab('lyapunov')" not in html
