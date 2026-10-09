from pathlib import Path
import shutil

import pytest

from generate_julia_odesolver import generate_julia_code, normalize_solver_method


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"
TEMPLATE_DIR = ROOT / "templates"
CMDL_TEMPLATE = (TEMPLATE_DIR / "ode_dae_solver_cmdl.jl.template").read_text()
GUI_TEMPLATE = (TEMPLATE_DIR / "ode_dae_solver_gui.jl.template").read_text()


@pytest.mark.parametrize(
    "model_name, expected_problem, expected_solver",
    [
        ("pendulum_tsit5", "ODEProblem", "Tsit5()"),
        ("pendulum_ida", "DAEProblem", "IDA()"),
        ("lorenz_attractor_tsit5", "ODEProblem", "Tsit5()"),
        ("lorenz_attractor_ida", "DAEProblem", "IDA()"),
    ],
)
@pytest.mark.parametrize("gui_version", [False, True])
def test_requested_solver_is_rendered(
    tmp_path, monkeypatch, model_name, expected_problem, expected_solver, gui_version
):
    models = tmp_path / "models"
    models.mkdir()
    shutil.copy(MODEL_DIR / f"{model_name}.toml", models / f"{model_name}.toml")
    monkeypatch.chdir(tmp_path)

    template = GUI_TEMPLATE if gui_version else CMDL_TEMPLATE
    path = generate_julia_code(model_name, template, gui_version=gui_version)
    code = path.read_text()

    assert f"prob = {expected_problem}(" in code
    assert f"prob, {expected_solver};" in code

    if expected_problem == "ODEProblem":
        assert "prob = DAEProblem(" not in code
    else:
        assert "prob = ODEProblem(" not in code


def test_any_simple_differentialequations_algorithm_name_can_be_emitted(
    tmp_path, monkeypatch
):
    """The generator does not hard-code a small whitelist of ODE algorithms."""
    models = tmp_path / "models"
    models.mkdir()

    text = (MODEL_DIR / "pendulum_tsit5.toml").read_text()
    text = text.replace('model_name = "pendulum_tsit5"', 'model_name = "pendulum_vern7"')
    text = text.replace('method = "Tsit5"', 'method = "Vern7"')
    (models / "pendulum_vern7.toml").write_text(text)
    monkeypatch.chdir(tmp_path)

    path = generate_julia_code("pendulum_vern7", CMDL_TEMPLATE)
    code = path.read_text()

    assert "prob = ODEProblem(" in code
    assert "prob, Vern7();" in code


def test_solver_method_rejects_arbitrary_julia_source():
    assert normalize_solver_method("Tsit5") == ("Tsit5()", "Tsit5")
    assert normalize_solver_method("OrdinaryDiffEq.Vern7()") == (
        "OrdinaryDiffEq.Vern7()",
        "Vern7",
    )

    with pytest.raises(ValueError):
        normalize_solver_method("Tsit5(); rm(`important_file`)")


def test_command_line_output_is_buffered_and_sample_rate_is_independent(
    tmp_path, monkeypatch
):
    models = tmp_path / "models"
    models.mkdir()
    shutil.copy(MODEL_DIR / "pendulum_tsit5.toml", models / "pendulum_tsit5.toml")
    monkeypatch.chdir(tmp_path)

    path = generate_julia_code("pendulum_tsit5", CMDL_TEMPLATE)
    code = path.read_text()

    assert "saveat=output_dt" in code
    assert "save_everystep=false" in code
    assert 'open("models/pendulum_tsit5.csv", "w") do outfile' in code
    assert "flush(outfile)" not in code


def test_gui_flushes_periodically_not_on_every_output_row(tmp_path, monkeypatch):
    models = tmp_path / "models"
    models.mkdir()
    shutil.copy(MODEL_DIR / "pendulum_tsit5.toml", models / "pendulum_tsit5.toml")
    monkeypatch.chdir(tmp_path)

    path = generate_julia_code("pendulum_tsit5", GUI_TEMPLATE, gui_version=True)
    code = path.read_text()

    assert "const output_dt = 0.05" in code
    assert "const output_flush_every = 10" in code
    assert "output_rows_since_flush[] >= output_flush_every" in code
    # One periodic flush plus a final flush at shutdown; not one unconditional
    # flush in the row-writing body.
    assert code.count("flush(outfile)") == 2


def test_lyapunov_no_longer_uses_a_matrix_exponential(tmp_path, monkeypatch):
    models = tmp_path / "models"
    models.mkdir()
    shutil.copy(MODEL_DIR / "pendulum_tsit5.toml", models / "pendulum_tsit5.toml")
    monkeypatch.chdir(tmp_path)

    path = generate_julia_code("pendulum_tsit5", CMDL_TEMPLATE)
    code = path.read_text()

    assert "propagate_tangent_rk4!" in code
    assert "exp(J * delta_t)" not in code
    assert "k1 = J * v" in code
    assert "k4 = J * (v .+ h .* k3)" in code


def test_jacobian_is_taken_directly_from_explicit_rhs(tmp_path, monkeypatch):
    models = tmp_path / "models"
    models.mkdir()
    shutil.copy(MODEL_DIR / "pendulum_ida.toml", models / "pendulum_ida.toml")
    monkeypatch.chdir(tmp_path)

    path = generate_julia_code("pendulum_ida", CMDL_TEMPLATE)
    code = path.read_text()

    assert "ForwardDiff.jacobian(u_var -> rhs_vector(u_var, p, t), u)" in code
    assert "J_ode = -J_residual" not in code
    assert "out[1] = du[1] - out[1]" in code


def test_length_parameter_cannot_shadow_base_length(tmp_path, monkeypatch):
    models = tmp_path / "models"
    models.mkdir()
    shutil.copy(MODEL_DIR / "pendulum_tsit5.toml", models / "pendulum_tsit5.toml")
    monkeypatch.chdir(tmp_path)

    path = generate_julia_code("pendulum_tsit5", CMDL_TEMPLATE)
    code = path.read_text()

    assert "Base.length(callbacks)" in code
    assert "length(callbacks) == 1" in code  # occurs only as part of Base.length
