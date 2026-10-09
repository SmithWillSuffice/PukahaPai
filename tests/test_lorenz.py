#!/usr/bin/env python3
"""
Integration/regression tests for the Lorenz attractor model.

These tests exercise the production command-line path:

    lorenz_attractor.toml
        -> generate_julia_odesolver.py
        -> models/lorenz_attractor_cmdl.jl
        -> Julia solver
        -> models/lorenz_attractor.csv

The generator is invoked through ``sys.executable`` so the tests do not depend
on the executable permission bit of generate_julia_odesolver.py.

The numerical checks are intentionally solver-robust.  They do not compare
against old IDA internal-step locations; the current command-line solver writes
the public trajectory on the configured ``output_dt`` grid.
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


MODEL_NAME = "lorenz_attractor"
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
def lorenz_config():
    assert MODEL_FILE.exists(), f"Model file not found: {MODEL_FILE}"
    return load_toml(MODEL_FILE)


@pytest.fixture(scope="module")
def generated_and_run(lorenz_config):
    """Generate the Julia command-line solver and run it once for this module."""
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
    assert rows, "Lorenz CSV contains no data rows"

    return {
        "config": lorenz_config,
        "julia_source": JULIA_SCRIPT.read_text(),
        "header": header,
        "rows": rows,
        "generation": gen_result,
        "run": run_result,
    }


def test_generate_julia_cmdl(generated_and_run):
    """The Lorenz TOML should generate an ODEProblem using its requested solver."""
    cfg = generated_and_run["config"]
    source = generated_and_run["julia_source"]

    method = cfg.get("solver", {}).get("method", "Tsit5")
    method_name = str(method).strip()
    if method_name.endswith("()"):
        method_name = method_name[:-2]

    assert "prob = ODEProblem(" in source
    assert f"prob, {method_name}()" in source

    # Diagnostic callbacks must not inject duplicate saved solution points.
    assert "save_positions=(false, false)" in source


def test_csv_output_format(generated_and_run):
    """The saved command-line trajectory should have the expected CSV schema."""
    header = generated_and_run["header"]
    rows = generated_and_run["rows"]

    assert header == ["t", "x", "y", "z"]
    assert len(rows) > 5

    for i, row in enumerate(rows[:5]):
        assert len(row) == 4, f"Row {i} should have 4 columns, got {len(row)}"
        assert all(math.isfinite(value) for value in row), (
            f"Row {i} contains a non-finite value: {row}"
        )


def test_csv_output_time_grid_and_initial_condition(generated_and_run):
    """
    The command-line CSV is sampled at output_dt, defaulting to solver dt.

    This checks the public output grid rather than the old IDA internal-step
    times such as 9.765625e-6.
    """
    cfg = generated_and_run["config"]
    rows = generated_and_run["rows"]

    t0 = float(cfg["tspan"]["t0"])
    t1 = float(cfg["tspan"]["t1"])
    solver_cfg = cfg["solver"]
    dt = float(solver_cfg.get("dt", 0.01))
    output_dt = float(solver_cfg.get("output_dt", dt))

    x0 = float(cfg["initial_conditions"]["x"])
    y0 = float(cfg["initial_conditions"]["y"])
    z0 = float(cfg["initial_conditions"]["z"])

    first = rows[0]
    last = rows[-1]

    assert first[0] == pytest.approx(t0, abs=1.0e-12)
    assert first[1] == pytest.approx(x0, abs=1.0e-12)
    assert first[2] == pytest.approx(y0, abs=1.0e-12)
    assert first[3] == pytest.approx(z0, abs=1.0e-12)

    assert last[0] == pytest.approx(
        t1, abs=max(1.0e-10, output_dt * 1.0e-8)
    )

    for previous, current in zip(rows[:5], rows[1:6]):
        assert current[0] - previous[0] == pytest.approx(
            output_dt, rel=1.0e-8, abs=1.0e-10
        )


def test_csv_output_values_are_physically_consistent(generated_and_run):
    """
    Check early Lorenz dynamics without hard-coding one solver's exact values.

    For the standard initial condition x=1, y=0, z=0 and positive
    sigma, rho, beta:

        dx/dt = sigma (y - x) < 0
        dy/dt = x (rho - z) - y > 0
        dz/dt = x y - beta z = 0 initially

    Thus the first saved step should have x decreased, y increased, and z
    non-negative.  The trajectory should then leave the initial state and remain
    finite over the saved simulation.
    """
    cfg = generated_and_run["config"]
    rows = generated_and_run["rows"]
    p = cfg["parameters"]

    sigma = float(p["sigma"])
    rho = float(p["rho"])
    beta = float(p["beta"])

    assert sigma > 0.0
    assert rho > 0.0
    assert beta > 0.0
    assert len(rows) >= 2

    initial = rows[0]
    next_row = rows[1]

    assert next_row[1] < initial[1]   # x initially decreases
    assert next_row[2] > initial[2]   # y initially increases
    assert next_row[3] >= initial[3]  # z starts non-negative

    # Ensure the trajectory actually evolves away from the initial condition.
    assert any(
        abs(row[1] - initial[1]) > 1.0e-3
        or abs(row[2] - initial[2]) > 1.0e-3
        or abs(row[3] - initial[3]) > 1.0e-3
        for row in rows[1:min(len(rows), 100)]
    )

    # A broad sanity bound catches gross solver/generator failures without
    # pretending chaotic trajectories should match bit-for-bit across methods.
    for row in rows:
        assert all(math.isfinite(value) for value in row)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
