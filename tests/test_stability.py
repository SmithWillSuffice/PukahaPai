from pathlib import Path

import numpy as np
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    tomllib = None
    import toml

from stability import (
    is_locally_stable,
    max_real_eigenvalue,
    residual_to_ode_jacobian,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"
TEMPLATE_DIR = ROOT / "templates"


def load_toml(path):
    if tomllib is not None:
        with Path(path).open("rb") as f:
            return tomllib.load(f)
    return toml.load(path)


def pendulum_jacobian(theta, config):
    p = config["parameters"]
    damping = p["damping"]
    g = p["g"]
    length = p["length"]
    return np.array([
        [0.0, 1.0],
        [-(g / length) * np.cos(theta), -damping],
    ])


def lorenz_jacobian(x, y, z, config):
    p = config["parameters"]
    sigma = p["sigma"]
    rho = p["rho"]
    beta = p["beta"]
    return np.array([
        [-sigma, sigma, 0.0],
        [rho - z, -1.0, -x],
        [y, x, -beta],
    ])


def test_pendulum_equilibrium_is_locally_stable():
    config = load_toml(MODEL_DIR / "pendulum.toml")
    j_ode = pendulum_jacobian(theta=0.0, config=config)
    eigs = np.linalg.eigvals(j_ode)

    assert is_locally_stable(eigs)
    assert max_real_eigenvalue(eigs) < 0.0


def test_old_residual_sign_would_misclassify_stable_pendulum():
    """Regression test for the original DAE-residual Jacobian sign bug."""
    config = load_toml(MODEL_DIR / "pendulum.toml")
    j_ode = pendulum_jacobian(theta=0.0, config=config)

    # Generated DAE residual is F(du,u) = du - f(u), hence dF/du = -df/du.
    j_residual = -j_ode

    old_eigs = np.linalg.eigvals(j_residual)
    corrected_j = residual_to_ode_jacobian(j_residual)
    corrected_eigs = np.linalg.eigvals(corrected_j)

    # The old code used eigvals(J_residual) and therefore got the wrong sign.
    assert max_real_eigenvalue(old_eigs) > 0.0
    assert is_locally_stable(corrected_eigs)
    assert np.allclose(corrected_j, j_ode)


def test_standard_lorenz_parameters_have_unstable_origin():
    """
    The usual sigma=10, rho=28 Lorenz regime is not a stable control case.
    Its origin is an unstable equilibrium (rho > 1).
    """
    config = load_toml(MODEL_DIR / "lorenz_attractor.toml")
    j_ode = lorenz_jacobian(0.0, 0.0, 0.0, config)
    eigs = np.linalg.eigvals(j_ode)

    assert max_real_eigenvalue(eigs) > 0.0
    assert not is_locally_stable(eigs)


def test_lorenz_unstable_model_starts_at_unstable_equilibrium():
    config = load_toml(MODEL_DIR / "lorenz_attractor_unstable.toml")
    ic = config["initial_conditions"]

    assert ic == {"x": 0.0, "y": 0.0, "z": 0.0}

    j_ode = lorenz_jacobian(ic["x"], ic["y"], ic["z"], config)
    eigs = np.linalg.eigvals(j_ode)

    assert max_real_eigenvalue(eigs) > 0.0
    assert not is_locally_stable(eigs)


def test_both_julia_templates_differentiate_explicit_rhs_directly():
    """
    Regression test for the old residual-Jacobian sign bug.

    The generated templates now construct an explicit rhs! even when IDA is
    selected, so stability differentiates f(u,t) directly and no residual-sign
    conversion is needed in generated Julia code.
    """
    for name in (
        "ode_dae_solver_cmdl.jl.template",
        "ode_dae_solver_gui.jl.template",
    ):
        text = (TEMPLATE_DIR / name).read_text()
        assert "ForwardDiff.jacobian(u_var -> rhs_vector(u_var, p, t), u)" in text
        assert "J_ode = -J_residual" not in text
        assert "return eigvals(compute_ode_jacobian(integrator))" in text
