# -*- coding: utf-8 -*-
'''
lyapunov
========
Post-processing utilities for the largest Lyapunov exponent written by the
Julia model solver.

The generated solver evolves one tangent vector v along the numerical
trajectory using the variational equation

    dv/dt = J(t) v,

where J(t) = df/du is the ODE Jacobian.  The vector is periodically
renormalized (Benettin-style), and the accumulated finite-time estimate

    lambda_max(t) = (1 / elapsed_time) * sum(log(stretch_factor))

is written to ``models/<model>_lyapunov.csv``.

This module does not recompute the exponent.  It loads that CSV, produces a
Plotly convergence plot, and writes a compact HTML interpretation suitable for
embedding in ``plots4model.py``.

A positive largest Lyapunov exponent means exponential sensitivity to nearby
initial states.  In a bounded non-equilibrium attractor this is evidence for
chaos, but a positive exponent by itself does not distinguish chaos from an
unstable equilibrium or a transient instability.

Copyright: (c) 2025-2026 Bijou M. Smith
License: GNU General Public License v3.0 <https://www.gnu.org/licenses/gpl-3.0.html>
'''

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go


LYAPUNOV_TOL = 1.0e-3
TAIL_FRACTION = 0.20


@dataclass(frozen=True)
class LyapunovSummary:
    final: float
    tail_mean: float
    tail_std: float
    n_samples: int
    t_start: float
    t_end: float
    classification: str


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


def _interpretation_html(summary):
    if summary.classification == "exponentially sensitive":
        return (
            "<p><strong>Interpretation:</strong> the estimated largest Lyapunov "
            "exponent is positive, so nearby trajectories separate exponentially. "
            "For a bounded non-equilibrium attractor this supports a diagnosis of "
            "deterministic chaos. A positive exponent alone can also describe an "
            "unstable equilibrium or transient, so it should be interpreted together "
            "with the trajectory and local stability plots.</p>"
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


def generate_lyapunov_report_html(model_name, lyap_df, config=None):
    """Write a compact HTML report and return its path."""
    summary = summarize_lyapunov(lyap_df)
    lyap_cfg = (config or {}).get("lyapunov", {})

    transient = lyap_cfg.get("transient")
    renorm_dt = lyap_cfg.get("renormalize_dt")

    html = [
        f"<h2>Lyapunov Analysis for Model: <code style='font-size: 150%'>{model_name}</code></h2>",
        f"<p><strong>Analysis time range:</strong> {summary.t_start:.6g} to {summary.t_end:.6g}</p>",
        f"<p><strong>Recorded estimates:</strong> {summary.n_samples}</p>",
        f"<p><strong>Final λ<sub>max</sub>:</strong> {summary.final:.6g}</p>",
        f"<p><strong>Mean over final {int(TAIL_FRACTION * 100)}%:</strong> {summary.tail_mean:.6g}</p>",
        f"<p><strong>Tail standard deviation:</strong> {summary.tail_std:.6g}</p>",
        f"<p><strong>Classification:</strong> {summary.classification}</p>",
    ]

    if transient is not None:
        html.append(f"<p><strong>Discarded transient:</strong> {transient}</p>")
    if renorm_dt is not None:
        html.append(f"<p><strong>Renormalization interval:</strong> {renorm_dt}</p>")

    html.append(_interpretation_html(summary))
    html.append(
        "<p><em>Method:</em> one tangent vector is evolved with the ODE Jacobian "
        "and periodically renormalized. The plotted quantity is the accumulated "
        "finite-time estimate of the largest Lyapunov exponent.</p>"
    )

    path = os.path.join("models", f"{model_name}_lyapunov_report.html")
    with open(path, "w") as f:
        f.write("\n".join(html))
    return path


__all__ = [
    "LYAPUNOV_TOL",
    "TAIL_FRACTION",
    "LyapunovSummary",
    "load_lyapunov",
    "classify_lyapunov",
    "summarize_lyapunov",
    "generate_lyapunov_figures",
    "generate_lyapunov_report_html",
]
