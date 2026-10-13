import numpy as np
import pandas as pd
import pytest

from lyapunov import (
    ChaosSummary,
    LyapunovSummary,
    _zero_one_statistic,
    assess_chaos,
)


def _positive_lyapunov():
    return LyapunovSummary(
        final=0.1,
        tail_mean=0.1,
        tail_std=0.005,
        n_samples=200,
        t_start=5.0,
        t_end=50.0,
        classification="exponentially sensitive",
    )


def test_zero_one_periodic_signal_is_regular():
    t = np.linspace(0.0, 200.0, 4000)
    x = np.sin(t)
    K = _zero_one_statistic(x)
    assert K is not None
    assert K < 0.50


def test_zero_one_logistic_map_is_chaotic():
    x = np.empty(5000)
    x[0] = 0.1234567
    for i in range(len(x) - 1):
        x[i + 1] = 4.0 * x[i] * (1.0 - x[i])

    K = _zero_one_statistic(x[500:])
    assert K is not None
    assert K > 0.70


def test_positive_lyapunov_at_constant_state_is_not_called_chaos():
    t = np.linspace(0.0, 50.0, 501)
    df = pd.DataFrame({"t": t, "x": np.zeros_like(t)})
    config = {
        "variables": {"names": ["x"]},
        "lyapunov": {"transient": 5.0},
        "equations": {"ode": {"f_x": "x"}},
    }

    result = assess_chaos(_positive_lyapunov(), df, config)

    assert result.equilibrium_like is True
    assert result.classification == "exponentially sensitive; equilibrium-like trajectory"


def test_strongly_drifting_positive_lyapunov_is_not_called_chaos():
    t = np.linspace(0.0, 50.0, 501)
    df = pd.DataFrame({"t": t, "x": 1.0 + 0.2 * t})
    config = {
        "variables": {"names": ["x"]},
        "lyapunov": {"transient": 5.0},
        "equations": {"ode": {"f_x": "0.2"}},
    }

    result = assess_chaos(_positive_lyapunov(), df, config)

    assert result.bounded_window is False
    assert "x" in result.drifting_variables
    assert result.classification == "exponentially sensitive; chaos not established"


def test_explicit_time_dependence_is_reported():
    t = np.linspace(0.0, 50.0, 501)
    x = np.sin(t)
    df = pd.DataFrame({"t": t, "x": x})
    config = {
        "variables": {"names": ["x"]},
        "lyapunov": {"transient": 5.0},
        "equations": {"auxiliary": {"driver": "exp(0.01*t)"}, "ode": {"f_x": "driver-x"}},
    }

    result = assess_chaos(_positive_lyapunov(), df, config)

    assert result.explicit_time_dependence is True
