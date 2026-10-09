#!/usr/bin/env python3
"""
Integration/regression tests for the pendulum model.

These tests exercise the production command-line path:

    pendulum.toml
        -> generate_julia_odesolver.py
        -> models/pendulum_cmdl.jl
        -> Julia solver
        -> models/pendulum.csv

The test deliberately invokes the Python generator through ``sys.executable``
rather than relying on the executable bit of generate_julia_odesolver.py.
This makes the test independent of file permissions after copying/unpacking
the project.

The numerical assertions are solver-aware but not tied to old IDA internal
step locations.  The current command-line solver writes samples at
``[solver].output_dt`` (defaulting to ``dt``), so the test checks the saved
time grid, initial condition, finite output, and basic damped-pendulum
behaviour rather than hard-coding obsolete IDA internal-step values.
"""

import csv
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    tomllib = None
    import toml


MODEL_NAME = "pendulum"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = PROJECT_ROOT / "generate_julia_odesolver.py"
MODEL_FILE = PROJECT_ROOT / "models" / f"{MODEL_NAME}.toml"
JULIA_SCRIPT = PROJECT_ROOT / "models" / f"{MODEL_NAME}_cmdl.jl"
CSV_OUTPUT = PROJECT_ROOT / "models" / f"{MODEL_NAME}.csv"


def load_toml(path):
    if tomllib is not None:
        with Path(path).open("rb") as f:
            return tomllib.load(f)
    return toml.load(path)


def read_csv_rows(path):
    with Path(path).open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [[float(value) for value in row] for row in reader]
    return header, rows


@pytest.fixture(scope="module")
def pendulum_config():
    assert MODEL_FILE.exists(), f"Model file not found: {MODEL_FILE}"
    return load_toml(MODEL_FILE)


@pytest.fixture(scope="module")
def generated_and_run(pendulum_config):
    """
    Generate the Julia command-line solver and run it once for this module.

    The generator is a Python script, so call it with the same Python
    interpreter running pytest.  This avoids requiring chmod +x.
    """
    assert GENERATOR.exists(), f"Generator not found: {GENERATOR}"

    gen_result = subprocess.run(
        [sys.executable, str(GENERATOR), MODEL_NAME],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=PROJECT_ROOT,
    )
    assert gen_result.returncode == 0, (
        "Julia code generation failed.\n"
        f"stdout:\n{gen_result.stdout}\n"
        f"stderr:\n{gen_result.stderr}"
    )

    assert JULIA_SCRIPT.exists(), f"Generated Julia file not found: {JULIA_SCRIPT}"

    julia = shutil.which("julia")
    if julia is None:
        pytest.skip("Julia executable is not available on PATH")

    if CSV_OUTPUT.exists():
        CSV_OUTPUT.unlink()

    run_result = subprocess.run(
        [julia, str(JULIA_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=PROJECT_ROOT,
    )
    assert run_result.returncode == 0, (
        "Julia simulation failed.\n"
        f"stdout:\n{run_result.stdout}\n"
        f"stderr:\n{run_result.stderr}"
    )

    assert CSV_OUTPUT.exists(), f"CSV output file not generated: {CSV_OUTPUT}"

    header, rows = read_csv_rows(CSV_OUTPUT)
    assert rows, "Pendulum CSV contains no data rows"

    return {
        "config": pendulum_config,
        "julia_source": JULIA_SCRIPT.read_text(),
        "header": header,
        "rows": rows,
        "generation": gen_result,
        "run": run_result,
    }


def test_generate_julia_cmdl(generated_and_run):
    """The current pendulum TOML should generate an ODEProblem with its requested solver."""
    cfg = generated_and_run["config"]
    source = generated_and_run["julia_source"]

    method = cfg.get("solver", {}).get("method", "Tsit5")
    method_name = str(method).strip()
    if method_name.endswith("()"):
        method_name = method_name[:-2]

    assert "prob = ODEProblem(" in source
    assert f"prob, {method_name}()" in source

    # Regression for the previous collision with the pendulum parameter
    # `length = 1.0`: generated support code must qualify Base.length.
    assert "Base.length(callbacks)" in source


def test_csv_output_format(generated_and_run):
    """The saved command-line trajectory should have the expected CSV schema."""
    header = generated_and_run["header"]
    rows = generated_and_run["rows"]

    assert header == ["t", "theta", "omega"]
    assert len(rows) > 5

    for i, row in enumerate(rows[:5]):
        assert len(row) == 3, f"Row {i} should have 3 columns, got {len(row)}"
        assert all(math.isfinite(value) for value in row), (
            f"Row {i} contains a non-finite value: {row}"
        )


def test_csv_output_time_grid_and_initial_condition(generated_and_run):
    """
    Command-line output is sampled at output_dt, which defaults to solver dt.

    Do not compare against the old IDA internal timesteps such as 0.00015625:
    those were implementation details of the old hard-coded DAE solver.
    """
    cfg = generated_and_run["config"]
    rows = generated_and_run["rows"]

    t0 = float(cfg["tspan"]["t0"])
    t1 = float(cfg["tspan"]["t1"])
    solver_cfg = cfg["solver"]
    dt = float(solver_cfg.get("dt", 0.01))
    output_dt = float(solver_cfg.get("output_dt", dt))

    theta0 = float(cfg["initial_conditions"]["theta"])
    omega0 = float(cfg["initial_conditions"]["omega"])

    first = rows[0]
    last = rows[-1]

    assert first[0] == pytest.approx(t0, abs=1.0e-12)
    assert first[1] == pytest.approx(theta0, abs=1.0e-12)
    assert first[2] == pytest.approx(omega0, abs=1.0e-12)

    assert last[0] == pytest.approx(t1, abs=max(1.0e-10, output_dt * 1.0e-8))

    # Check the first few output spacings rather than assuming solver-internal
    # accepted steps.  saveat=output_dt defines the public CSV sampling grid.
    for previous, current in zip(rows[:5], rows[1:6]):
        assert current[0] - previous[0] == pytest.approx(
            output_dt, rel=1.0e-8, abs=1.0e-10
        )


def test_csv_output_values_are_physically_consistent(generated_and_run):
    """
    Regression checks that are robust across sensible ODE algorithms.

    Initially theta > 0 and omega = 0, so gravity gives a negative angular
    acceleration.  With positive damping, the mechanical energy must decrease
    over the long run and the state should approach the stable equilibrium.
    """
    cfg = generated_and_run["config"]
    rows = generated_and_run["rows"]
    p = cfg["parameters"]

    mass = float(p["mass"])
    length = float(p["length"])
    damping = float(p["damping"])
    g = float(p["g"])

    assert damping > 0.0
    assert len(rows) >= 2

    # Immediately after release from positive angle, angular velocity should
    # become negative and theta should start moving toward zero.
    theta_initial = rows[0][1]
    theta_next = rows[1][1]
    omega_next = rows[1][2]

    assert omega_next < 0.0
    assert theta_next < theta_initial

    def energy(theta, omega):
        kinetic = 0.5 * mass * (length * omega) ** 2
        potential = mass * g * length * (1.0 - math.cos(theta))
        return kinetic + potential

    e_initial = energy(rows[0][1], rows[0][2])
    e_final = energy(rows[-1][1], rows[-1][2])

    assert e_final < e_initial

    # Over t=100 with damping=0.1, the reference pendulum should be close to
    # its stable rest state.  These are intentionally loose physical bounds,
    # not solver-specific bitwise regression values.
    assert abs(rows[-1][1]) < 0.05
    assert abs(rows[-1][2]) < 0.05


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
