import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
PLOT_UTILS = ROOT / "plot_utils.py"


def _load_plot_utils():
    spec = importlib.util.spec_from_file_location("plot_utils_under_test", PLOT_UTILS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_near_constant_axis_gets_padded_and_clean_range():
    mod = _load_plot_utils()

    values = np.array([
        0.12,
        0.12000000000000001,
        0.11999999999999995,
    ])

    options = mod._time_series_axis_options(values)

    assert options["range"] == pytest.approx([0.108, 0.132])
    assert options["tickformat"] == ".6~g"


def test_genuinely_varying_axis_keeps_plotly_autorange():
    mod = _load_plot_utils()

    values = np.array([0.12, 0.119, 0.121])

    options = mod._time_series_axis_options(values)

    assert "range" not in options
    assert options["tickformat"] == ".6~g"


def test_dual_axis_near_constant_series_uses_independent_padded_axis():
    mod = _load_plot_utils()

    df = pd.DataFrame({
        "t": [0.0, 1.0, 2.0],
        "lambda_G": [0.12, 0.12000000000000001, 0.11999999999999995],
        "lambda_JG": [0.04, 0.05, 0.06],
    })

    fig = mod.plot_dual_axis_time_series(
        df,
        "t",
        ["lambda_G", "lambda_JG"],
    )

    assert list(fig.layout.yaxis.range) == pytest.approx([0.108, 0.132])
    assert fig.layout.yaxis.tickformat == ".6~g"

    # lambda_JG genuinely varies, so its independent right-hand axis should
    # retain Plotly autoranging.
    assert fig.layout.yaxis2.range is None
    assert fig.layout.yaxis2.tickformat == ".6~g"
