'''
Unit test for the toml model parameter and IC validations

Passed 2026-10-08
```
 pytest -v tests/test_model_validation.py
 ...        
============ 12 passed in 0.22s ==========
```

| Copyright © 2026, Bijou M. Smith
| License: GNU General Public License v3.0  <https://www.gnu.org/licenses/gpl-3.0.html>
'''
from copy import deepcopy
from pathlib import Path
import shutil

import pytest

from model_validation import (
    ModelValidationError,
    get_model_limits,
    load_and_validate_model,
    validate_model_spec,
)
from generate_julia_odesolver import generate_julia_code

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"


def test_model_without_limits_is_valid():
    config = load_and_validate_model(MODEL_DIR / "mmm_0_4b.toml")

    assert config["model_name"] == "mmm_0_4b"
    assert get_model_limits(config) == {}
    assert get_model_limits(config, "parameters") == {}
    assert get_model_limits(config, "initial_conditions") == {}


def test_model_without_limits_does_not_enforce_constraints():
    config = load_and_validate_model(MODEL_DIR / "mmm_0_4b.toml")

    config["parameters"]["premium_F"] = -2.0
    config["initial_conditions"]["lambda_F"] = 1.5

    # No exception should be raised because this model declares no limits.
    validate_model_spec(config)


@pytest.mark.parametrize(
    "model_file",
    [
        "pendulum.toml",
        "lorenz_attractor.toml",
        "mmm_0_4.toml",
        "mmm_0_4b.toml",
    ],
)
def test_saved_models_satisfy_declared_limits(model_file):
    config = load_and_validate_model(MODEL_DIR / model_file)
    assert config["model_name"]


def test_mmm_0_4_premium_F_strict_lower_bound():
    config = load_and_validate_model(MODEL_DIR / "mmm_0_4.toml")

    good = deepcopy(config)
    good["parameters"]["premium_F"] = -0.999
    validate_model_spec(good)

    bad = deepcopy(config)
    bad["parameters"]["premium_F"] = -1.0
    with pytest.raises(ModelValidationError, match=r"premium_F > -1\.0"):
        validate_model_spec(bad)


def test_mmm_0_4_lambda_F_initial_condition_bounds():
    config = load_and_validate_model(MODEL_DIR / "mmm_0_4.toml")

    for value in (0.0, 1.0):
        edge = deepcopy(config)
        edge["initial_conditions"]["lambda_F"] = value
        validate_model_spec(edge)

    bad = deepcopy(config)
    bad["initial_conditions"]["lambda_F"] = 1.01
    with pytest.raises(ModelValidationError, match=r"lambda_F <= 1\.0"):
        validate_model_spec(bad)


def test_pendulum_limits():
    config = load_and_validate_model(MODEL_DIR / "pendulum.toml")

    bad_length = deepcopy(config)
    bad_length["parameters"]["length"] = 0.0
    with pytest.raises(ModelValidationError, match=r"length > 0\.0"):
        validate_model_spec(bad_length)

    bad_damping = deepcopy(config)
    bad_damping["parameters"]["damping"] = -0.01
    with pytest.raises(ModelValidationError, match=r"damping >= 0\.0"):
        validate_model_spec(bad_damping)


def test_lorenz_parameter_limits():
    config = load_and_validate_model(MODEL_DIR / "lorenz_attractor.toml")

    for name, bad_value in (("sigma", 0.0), ("beta", 0.0), ("rho", -0.01)):
        bad = deepcopy(config)
        bad["parameters"][name] = bad_value
        with pytest.raises(ModelValidationError):
            validate_model_spec(bad)


def test_limit_metadata_is_available_for_future_gui():
    config = load_and_validate_model(MODEL_DIR / "mmm_0_4.toml")
    limits = get_model_limits(config, "parameters")

    assert limits["premium_F"]["min"] == -1.0
    assert limits["premium_F"]["min_inclusive"] is False


def test_generator_rejects_invalid_model_before_writing_julia(tmp_path, monkeypatch):
    models = tmp_path / "models"
    models.mkdir()

    text = (MODEL_DIR / "mmm_0_4.toml").read_text()
    text = text.replace("premium_F = 0.0", "premium_F = -1.0")
    (models / "mmm_0_4.toml").write_text(text)

    monkeypatch.chdir(tmp_path)

    with pytest.raises(ModelValidationError):
        generate_julia_code("mmm_0_4", "THIS TEMPLATE MUST NOT BE RENDERED")

    assert not (models / "mmm_0_4_cmdl.jl").exists()
