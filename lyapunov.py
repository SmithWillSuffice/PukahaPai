# -*- coding: utf-8 -*-
"""
lyapunov
========
Post-processing utilities for the largest Lyapunov exponent written by the
Julia model solver, plus a conservative finite-data chaos diagnostic.

The Julia solver supplies the finite-time largest Lyapunov exponent.  This
module does not recompute that exponent.

A positive largest Lyapunov exponent establishes exponential sensitivity of
nearby trajectories.  It does *not* by itself establish chaos.  To distinguish
the two cases more carefully, this module can also examine the saved simulation
trajectory and apply a modified 0-1 test for chaos together with finite-window
checks for equilibrium-like and strongly drifting behaviour.

No finite numerical test proves mathematical chaos.  The strongest label used
here is therefore "chaos supported", never "chaos proven".

Copyright: (c) 2025-2026 Bijou M. Smith
License: GNU General Public License v3.0 <https://www.gnu.org/licenses/gpl-3.0.html>
"""

from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import plotly.graph_objects as go


LYAPUNOV_TOL = 1.0e-3
TAIL_FRACTION = 0.20

CHAOS_K_LOW = 0.50
CHAOS_K_HIGH = 0.70
CHAOS_MIN_SAMPLES = 120
CHAOS_C_VALUES = 32
CHAOS_RANDOM_SEED = 1729

_EQUILIBRIUM_REL_TOL = 1.0e-5
_TREND_R2_THRESHOLD = 0.90
_TREND_FRACTION_THRESHOLD = 0.80


@dataclass(frozen=True)
class LyapunovSummary:
    final: float
    tail_mean: float
    tail_std: float
    n_samples: int
    t_start: float
    t_end: float
    classification: str


@dataclass(frozen=True)
class ChaosSummary:
    classification: str
    k_median: float | None
    k_by_variable: dict[str, float] = field(default_factory=dict)
    n_samples: int = 0
    bounded_window: bool | None = None
    equilibrium_like: bool | None = None
    explicit_time_dependence: bool = False
    drifting_variables: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


def load_lyapunov(model_name):
    """Load ``models/<model_name>_lyapunov.csv`` or return ``None``."""
    path = os.path.join("models", f"{model_name}_lyapunov.csv")
    if not os.path.exists(path):
        return None

    df = pd.read_csv(path)
    required = {"t", "lambda_max"}
    if not required.issubset(df.columns):
        raise ValueError(
            f"Lyapunov CSV '{path}' must contain columns: t, lambda_max"
        )

    out = df.loc[:, ["t", "lambda_max"]].copy()
    out["t"] = pd.to_numeric(out["t"], errors="coerce")
    out["lambda_max"] = pd.to_numeric(out["lambda_max"], errors="coerce")
    out = out.replace([np.inf, -np.inf], np.nan).dropna()
    return out


def classify_lyapunov(value, tol=LYAPUNOV_TOL):
    """Classify the sign of a largest-Lyapunov-exponent estimate."""
    if not np.isfinite(value):
        return "unresolved"
    if value > tol:
        return "exponentially sensitive"
    if value < -tol:
        return "contracting"
    return "neutral / unresolved near zero"


def summarize_lyapunov(lyap_df, tol=LYAPUNOV_TOL, tail_fraction=TAIL_FRACTION):
    """
    Summarize convergence of the finite-time largest Lyapunov exponent.

    The tail mean is used for classification because a single final point can
    be noisier than the converged end of the series.  The final point is still
    reported explicitly.
    """
    if lyap_df is None or len(lyap_df) == 0:
        raise ValueError("No Lyapunov samples are available")

    vals = pd.to_numeric(lyap_df["lambda_max"], errors="coerce").to_numpy(float)
    times = pd.to_numeric(lyap_df["t"], errors="coerce").to_numpy(float)
    mask = np.isfinite(vals) & np.isfinite(times)
    vals = vals[mask]
    times = times[mask]

    if len(vals) == 0:
        raise ValueError("No finite Lyapunov samples are available")

    n_tail = max(1, int(np.ceil(len(vals) * tail_fraction)))
    tail = vals[-n_tail:]
    tail_mean = float(np.mean(tail))
    tail_std = float(np.std(tail, ddof=0))

    return LyapunovSummary(
        final=float(vals[-1]),
        tail_mean=tail_mean,
        tail_std=tail_std,
        n_samples=len(vals),
        t_start=float(times[0]),
        t_end=float(times[-1]),
        classification=classify_lyapunov(tail_mean, tol=tol),
    )


def _explicit_time_dependence(config):
    """
    Return True when a model equation contains an explicit standalone ``t``.

    This is a syntactic test of the supplied TOML representation.  A
    non-autonomous model can always be embedded in a higher-dimensional
    autonomous system by promoting the external drivers to states; this flag
    describes the model as currently written.
    """
    equations = (config or {}).get("equations", {})
    for section in ("auxiliary", "ode"):
        for expression in equations.get(section, {}).values():
            if isinstance(expression, str) and re.search(r"\bt\b", expression):
                return True
    return False


def _analysis_trajectory(trajectory_df, config, transient=None):
    """
    Return finite post-transient samples of the model's actual state variables.

    Derived variables are deliberately excluded by default.  They can contain
    algebraic duplicates, ratios or explicitly imposed trends that should not
    receive extra votes in the chaos test.
    """
    if trajectory_df is None or len(trajectory_df) == 0:
        return None, []

    df = trajectory_df.copy()
    if "t" not in df.columns:
        return None, []

    state_vars = list((config or {}).get("variables", {}).get("names", []))
    configured = (config or {}).get("lyapunov", {}).get("chaos_variables")
    if configured:
        state_vars = [v for v in configured if v in df.columns]
    else:
        state_vars = [v for v in state_vars if v in df.columns]

    if not state_vars:
        state_vars = [
            c for c in df.columns
            if c != "t" and pd.api.types.is_numeric_dtype(df[c])
        ]

    columns = ["t"] + state_vars
    df = df.loc[:, columns].copy()
    for c in columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan).dropna()

    if transient is not None:
        df = df.loc[df["t"] >= float(transient)]

    return df.reset_index(drop=True), state_vars


def _linear_detrend(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 2:
        return x.copy()

    index = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(index, x, 1)
    return x - (slope * index + intercept)


def _decorrelation_stride(x, min_remaining=CHAOS_MIN_SAMPLES):
    """
    Pick a modest stride for continuous-time data to reduce oversampling.

    The 0-1 test can underestimate chaos when a continuous trajectory is
    sampled far more rapidly than its decorrelation time.  We use the first
    lag whose autocorrelation falls below exp(-1), but never decimate below
    ``min_remaining`` observations.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 8:
        return 1

    y = x - np.mean(x)
    var = float(np.dot(y, y))
    if var <= np.finfo(float).eps:
        return 1

    max_lag = min(200, max(2, n // 10))
    target = np.exp(-1.0)
    candidate = 1
    for lag in range(1, max_lag + 1):
        ac = float(np.dot(y[:-lag], y[lag:]) / var)
        if ac <= target:
            candidate = lag
            break

    max_stride = max(1, n // max(min_remaining, 1))
    return max(1, min(candidate, max_stride))


def _zero_one_statistic(
    series,
    *,
    n_c=CHAOS_C_VALUES,
    seed=CHAOS_RANDOM_SEED,
    min_samples=CHAOS_MIN_SAMPLES,
):
    """
    Modified 0-1 test statistic K for one scalar observable.

    Returns ``None`` when the series is too short or essentially constant.

    The implementation uses the correlation form of the Gottwald-Melbourne
    statistic, multiple reproducible values of c, linear detrending, and
    modest automatic subsampling for continuous-time trajectories.
    """
    x = np.asarray(series, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < min_samples:
        return None

    x = _linear_detrend(x)
    scale = float(np.std(x))
    if scale <= max(1.0e-12, 1.0e-10 * max(1.0, np.max(np.abs(x)))):
        return None
    x = x / scale

    stride = _decorrelation_stride(x, min_remaining=min_samples)
    x = x[::stride]
    if len(x) < min_samples:
        return None

    # Remove any tiny mean reintroduced by subsampling.
    x = x - np.mean(x)

    N = len(x)
    n_max = max(10, N // 10)
    lags = np.arange(1, n_max + 1, dtype=float)
    j = np.arange(1, N + 1, dtype=float)

    rng = np.random.default_rng(seed)
    cs = rng.uniform(np.pi / 5.0, 4.0 * np.pi / 5.0, int(n_c))
    k_values = []

    for c in cs:
        p = np.cumsum(x * np.cos(j * c))
        q = np.cumsum(x * np.sin(j * c))

        M = np.empty(n_max, dtype=float)
        for idx, lag in enumerate(range(1, n_max + 1)):
            dp = p[lag:] - p[:-lag]
            dq = q[lag:] - q[:-lag]
            M[idx] = np.mean(dp * dp + dq * dq)

        if not np.all(np.isfinite(M)) or np.std(M) <= 1.0e-14:
            continue

        K = np.corrcoef(lags, M)[0, 1]
        if np.isfinite(K):
            k_values.append(float(K))

    if not k_values:
        return None

    return float(np.median(k_values))


def _equilibrium_like(df, state_vars):
    """True when every state is essentially constant over the final 20%."""
    if df is None or len(df) < 5 or not state_vars:
        return None

    tail = df.iloc[-max(5, int(np.ceil(0.20 * len(df)))):]
    variable_found = False

    for name in state_vars:
        full = df[name].to_numpy(float)
        vals = tail[name].to_numpy(float)

        full_scale = max(
            float(np.ptp(full)),
            float(np.std(full)),
            abs(float(np.mean(full))),
            1.0,
        )
        rel_span = float(np.ptp(vals)) / full_scale
        if rel_span > _EQUILIBRIUM_REL_TOL:
            variable_found = True
            break

    return not variable_found


def _drifting_variables(df, state_vars):
    """
    Detect strong secular drift over the finite post-transient window.

    This is deliberately conservative.  A state is marked as drifting only
    when a linear trend explains at least 90% of its variance *and* the fitted
    end-to-end trend accounts for at least 80% of its observed range.
    """
    if df is None or len(df) < 8:
        return ()

    index = np.arange(len(df), dtype=float)
    drifting = []

    for name in state_vars:
        y = df[name].to_numpy(float)
        span = float(np.ptp(y))
        if span <= max(1.0e-12, 1.0e-10 * max(1.0, np.max(np.abs(y)))):
            continue

        slope, intercept = np.polyfit(index, y, 1)
        fit = slope * index + intercept

        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        if ss_tot <= np.finfo(float).eps:
            continue

        ss_res = float(np.sum((y - fit) ** 2))
        r2 = 1.0 - ss_res / ss_tot
        trend_span = abs(float(slope)) * (len(y) - 1)
        trend_fraction = trend_span / span

        if r2 >= _TREND_R2_THRESHOLD and trend_fraction >= _TREND_FRACTION_THRESHOLD:
            drifting.append(name)

    return tuple(drifting)


def assess_chaos(
    lyap_summary,
    trajectory_df=None,
    config=None,
    *,
    k_low=CHAOS_K_LOW,
    k_high=CHAOS_K_HIGH,
    min_samples=CHAOS_MIN_SAMPLES,
):
    """
    Combine Lyapunov growth with finite-trajectory diagnostics.

    Classification is intentionally conservative:

    * positive LLE alone -> ``exponentially sensitive``;
    * positive LLE + equilibrium-like or strongly drifting trajectory ->
      chaos is not established;
    * positive LLE + bounded/non-drifting trajectory + high modified 0-1
      statistic -> ``chaos supported``;
    * intermediate 0-1 result -> inconclusive.

    The result is evidence-based, not a mathematical proof.
    """
    explicit_time = _explicit_time_dependence(config or {})

    if lyap_summary.classification != "exponentially sensitive":
        return ChaosSummary(
            classification=lyap_summary.classification,
            k_median=None,
            explicit_time_dependence=explicit_time,
            notes=("Chaos testing is only relevant when the largest Lyapunov exponent is positive.",),
        )

    lyap_cfg = (config or {}).get("lyapunov", {})
    transient = lyap_cfg.get("transient")
    traj, state_vars = _analysis_trajectory(trajectory_df, config or {}, transient)

    if traj is None or len(traj) < min_samples:
        return ChaosSummary(
            classification="exponentially sensitive; chaos test unresolved",
            k_median=None,
            n_samples=0 if traj is None else len(traj),
            explicit_time_dependence=explicit_time,
            notes=(
                f"At least {min_samples} post-transient trajectory samples are required "
                "for the finite-data chaos test.",
            ),
        )

    equilibrium = _equilibrium_like(traj, state_vars)
    drifting = _drifting_variables(traj, state_vars)
    bounded_window = len(drifting) == 0

    k_by_variable = {}
    for i, name in enumerate(state_vars):
        K = _zero_one_statistic(
            traj[name].to_numpy(float),
            min_samples=min_samples,
            seed=CHAOS_RANDOM_SEED + i,
        )
        if K is not None:
            k_by_variable[name] = K

    k_median = (
        float(np.median(list(k_by_variable.values())))
        if k_by_variable
        else None
    )

    notes = []

    if explicit_time:
        notes.append(
            "The model is explicitly time-dependent as written (non-autonomous); "
            "the chaos test is therefore interpreted more cautiously."
        )

    if equilibrium:
        classification = "exponentially sensitive; equilibrium-like trajectory"
        notes.append(
            "The saved state trajectory approaches or remains near a fixed state, "
            "so positive tangent growth is not sufficient evidence for chaos."
        )
    elif not bounded_window:
        classification = "exponentially sensitive; chaos not established"
        notes.append(
            "Strong secular drift was detected in: " + ", ".join(drifting) + "."
        )
        notes.append(
            "A finite drifting trajectory does not establish a bounded chaotic attractor."
        )
    elif k_median is None:
        classification = "exponentially sensitive; chaos test unresolved"
        notes.append(
            "No state variable supplied enough non-degenerate data for the modified 0-1 test."
        )
    elif k_median >= k_high:
        classification = "chaos supported"
        notes.append(
            "The positive Lyapunov exponent is accompanied by a high modified 0-1 "
            "chaos statistic on a non-drifting, non-equilibrium trajectory."
        )
    elif k_median <= k_low:
        classification = "exponentially sensitive; regular trajectory indicated"
        notes.append(
            "The modified 0-1 statistic is low, which is more consistent with "
            "regular/periodic behaviour than with a chaotic trajectory."
        )
    else:
        classification = "exponentially sensitive; chaos test inconclusive"
        notes.append(
            "The modified 0-1 statistic lies in the intermediate region and does "
            "not cleanly distinguish regular from chaotic dynamics."
        )

    return ChaosSummary(
        classification=classification,
        k_median=k_median,
        k_by_variable=k_by_variable,
        n_samples=len(traj),
        bounded_window=bounded_window,
        equilibrium_like=equilibrium,
        explicit_time_dependence=explicit_time,
        drifting_variables=drifting,
        notes=tuple(notes),
    )


def generate_lyapunov_figures(lyap_df):
    """Return Plotly figures for the finite-time largest Lyapunov exponent."""
    if lyap_df is None or len(lyap_df) == 0:
        return []

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=lyap_df["t"],
            y=lyap_df["lambda_max"],
            mode="lines",
            name="finite-time λmax",
        )
    )
    fig.add_hline(
        y=0.0,
        line=dict(dash="dash", color="red"),
        annotation_text="λmax = 0",
    )
    fig.update_layout(
        title="Finite-Time Largest Lyapunov Exponent",
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(
            title="t",
            showgrid=True,
            gridcolor="rgba(100, 100, 100, 0.3)",
            zeroline=True,
            zerolinecolor="rgba(100, 100, 100, 0.5)",
            zerolinewidth=1,
        ),
        yaxis=dict(
            title="λmax",
            showgrid=True,
            gridcolor="rgba(100, 100, 100, 0.3)",
            zeroline=True,
            zerolinecolor="rgba(100, 100, 100, 0.5)",
            zerolinewidth=1,
        ),
        paper_bgcolor="black",
        plot_bgcolor="black",
        font=dict(color="white"),
        autosize=True,
    )
    return [fig]


def _interpretation_html(summary, chaos=None):
    if summary.classification == "exponentially sensitive":
        if chaos is not None and chaos.classification == "chaos supported":
            return (
                "<p><strong>Interpretation:</strong> nearby trajectories separate "
                "exponentially and the saved trajectory also passes the finite-data "
                "chaos checks used here. This <strong>supports</strong> a diagnosis "
                "of deterministic chaos; it is not a mathematical proof.</p>"
            )

        return (
            "<p><strong>Interpretation:</strong> the estimated largest Lyapunov "
            "exponent is positive, so nearby trajectories separate exponentially. "
            "This establishes exponential sensitivity, but does not by itself "
            "establish deterministic chaos.</p>"
        )

    if summary.classification == "contracting":
        return (
            "<p><strong>Interpretation:</strong> the estimated largest Lyapunov "
            "exponent is negative, so nearby trajectories contract on average over "
            "the analysed interval.</p>"
        )

    return (
        "<p><strong>Interpretation:</strong> the estimate is close to zero at the "
        "configured numerical tolerance. This can indicate neutral dynamics, slow "
        "convergence, or an analysis interval that is too short.</p>"
    )


def _chaos_report_html(chaos):
    if chaos is None:
        return ""

    parts = [
        "<h3>Chaos diagnostic</h3>",
        f"<p><strong>Dynamical diagnosis:</strong> {html.escape(chaos.classification)}</p>",
    ]

    if chaos.k_median is not None:
        parts.append(
            f"<p><strong>Modified 0-1 statistic K (median over usable states):</strong> "
            f"{chaos.k_median:.4g}</p>"
        )
        if chaos.k_by_variable:
            details = ", ".join(
                f"{html.escape(name)}={value:.3g}"
                for name, value in chaos.k_by_variable.items()
            )
            parts.append(
                f"<p><strong>Per-state K:</strong> <code>{details}</code></p>"
            )

    if chaos.n_samples:
        parts.append(
            f"<p><strong>Trajectory samples used:</strong> {chaos.n_samples}</p>"
        )

    if chaos.bounded_window is not None:
        wording = "yes" if chaos.bounded_window else "no"
        parts.append(
            "<p><strong>No strong secular drift over analysed window:</strong> "
            f"{wording}</p>"
        )

    if chaos.equilibrium_like is not None:
        wording = "yes" if chaos.equilibrium_like else "no"
        parts.append(
            f"<p><strong>Equilibrium-like tail:</strong> {wording}</p>"
        )

    if chaos.explicit_time_dependence:
        parts.append(
            "<p><strong>Model form:</strong> explicitly time-dependent "
            "(non-autonomous as written).</p>"
        )

    if chaos.notes:
        parts.append("<ul>")
        for note in chaos.notes:
            parts.append(f"<li>{html.escape(note)}</li>")
        parts.append("</ul>")

    parts.append(
        "<p><em>0-1 interpretation:</em> K near 0 is associated with regular "
        "dynamics; K near 1 is associated with chaotic dynamics. PukahaPai uses "
        f"K ≤ {CHAOS_K_LOW:g} as regular evidence and K ≥ {CHAOS_K_HIGH:g} as "
        "chaotic evidence. Intermediate values are reported as inconclusive.</p>"
    )
    parts.append(
        "<p><em>Caution:</em> boundedness and chaos cannot be proved from a finite "
        "CSV trajectory. The test is a numerical diagnostic and should be checked "
        "for convergence with longer runs and smaller timesteps.</p>"
    )

    return "\n".join(parts)


def generate_lyapunov_report_html(
    model_name,
    lyap_df,
    config=None,
    trajectory_df=None,
):
    """Write a compact HTML Lyapunov/chaos report and return its path."""
    summary = summarize_lyapunov(lyap_df)
    lyap_cfg = (config or {}).get("lyapunov", {})

    transient = lyap_cfg.get("transient")
    renorm_dt = lyap_cfg.get("renormalize_dt")

    chaos_enabled = bool(lyap_cfg.get("chaos_test", True))
    chaos = (
        assess_chaos(summary, trajectory_df=trajectory_df, config=config or {})
        if chaos_enabled
        else None
    )

    html_parts = [
        f"<h2>Lyapunov Analysis for Model: <code style='font-size: 150%'>{model_name}</code></h2>",
        f"<p><strong>Analysis time range:</strong> {summary.t_start:.6g} to {summary.t_end:.6g}</p>",
        f"<p><strong>Recorded estimates:</strong> {summary.n_samples}</p>",
        f"<p><strong>Final λ<sub>max</sub>:</strong> {summary.final:.6g}</p>",
        f"<p><strong>Mean over final {int(TAIL_FRACTION * 100)}%:</strong> {summary.tail_mean:.6g}</p>",
        f"<p><strong>Tail standard deviation:</strong> {summary.tail_std:.6g}</p>",
        f"<p><strong>Lyapunov classification:</strong> {summary.classification}</p>",
    ]

    if transient is not None:
        html_parts.append(
            f"<p><strong>Discarded transient:</strong> {float(transient):.6g}</p>"
        )
    if renorm_dt is not None:
        html_parts.append(
            f"<p><strong>Renormalization interval:</strong> {float(renorm_dt):.6g}</p>"
        )

    html_parts.append(_interpretation_html(summary, chaos))
    if chaos_enabled:
        html_parts.append(_chaos_report_html(chaos))

    html_parts.append(
        "<p><em>Lyapunov method:</em> one tangent vector is evolved with the ODE "
        "Jacobian and periodically renormalized. The plotted quantity is the "
        "accumulated finite-time estimate of the largest Lyapunov exponent.</p>"
    )

    path = os.path.join("models", f"{model_name}_lyapunov_report.html")
    with open(path, "w") as f:
        f.write("\n".join(html_parts))
    return path


__all__ = [
    "LYAPUNOV_TOL",
    "TAIL_FRACTION",
    "CHAOS_K_LOW",
    "CHAOS_K_HIGH",
    "CHAOS_MIN_SAMPLES",
    "LyapunovSummary",
    "ChaosSummary",
    "load_lyapunov",
    "classify_lyapunov",
    "summarize_lyapunov",
    "assess_chaos",
    "generate_lyapunov_figures",
    "generate_lyapunov_report_html",
]
