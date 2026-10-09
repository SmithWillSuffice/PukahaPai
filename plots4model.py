#!/usr/bin/env python3
'''
plots4model
===========
Generate a self-contained browser report for a model simulation using Plotly.

The default report has three tabs:

    Dynamics | Stability | Lyapunov

``[plots].combine_stability_lyapunov_plots = true`` combines the last two
into a single ``Stability & Lyapunov`` tab.

Example:
    ./plots4model.py pendulum

Copyright: (c) 2025-2026 Bijou M. Smith
License: GNU General Public License v3.0 <https://www.gnu.org/licenses/gpl-3.0.html>
'''

import os

import pandas as pd
import plotly.io as pio

from stability import (
    load_eigenvalues,
    generate_stability_figures,
    generate_stability_report_html,
)
from lyapunov import (
    load_lyapunov,
    generate_lyapunov_figures,
    generate_lyapunov_report_html,
)
from plot_utils import (
    load_config,
    compute_derived_variables,
    plot_time_series,
    plot_phase_2d,
    plot_phase_3d,
)


INACTIVE_TAB = "#1E90FF"   # dodger blue
ACTIVE_TAB = "#70C1A3"     # pale/soft green
TITLE_BLUE = "#4997d0"


def _read_text(path):
    with open(path) as f:
        return f.read()


def _figures_html(figures):
    parts = []
    for fig in figures:
        parts.append('<div class="plot-container">')
        parts.append(
            pio.to_html(
                fig,
                include_plotlyjs=False,
                full_html=False,
                config={"responsive": True},
            )
        )
        parts.append("</div>")
    return "\n".join(parts)


def _stability_content(model_name, config):
    enabled = config.get("eigenvalues", {}).get("all", False)
    eig_df = load_eigenvalues(model_name)

    if enabled and eig_df is not None and not eig_df.empty:
        figures = generate_stability_figures(eig_df)
        report_path = generate_stability_report_html(model_name, eig_df)
        return _figures_html(figures) + f'<div class="analysis-report">{_read_text(report_path)}</div>'

    if enabled:
        msg = (
            "Stability analysis is enabled, but no eigenvalue CSV was found. "
            "Run the generated Julia solver before building the HTML report."
        )
    else:
        msg = (
            "No local Jacobian stability analysis is enabled for this model."
            "<pre>[eigenvalues]\nall = true</pre>"
        )
    return f'<div class="analysis-report"><h2>Stability Analysis</h2><p>{msg}</p></div>'


def _lyapunov_content(model_name, config):
    enabled = bool(config.get("lyapunov", {}).get("enabled", False))
    lyap_df = load_lyapunov(model_name)

    if enabled and lyap_df is not None and not lyap_df.empty:
        figures = generate_lyapunov_figures(lyap_df)
        report_path = generate_lyapunov_report_html(model_name, lyap_df, config=config)
        return _figures_html(figures) + f'<div class="analysis-report">{_read_text(report_path)}</div>'

    if enabled:
        msg = (
            "Lyapunov analysis is enabled, but no Lyapunov CSV was found. "
            "Run the generated Julia solver before building the HTML report."
        )
    else:
        msg = (
            "No Lyapunov analysis is enabled for this model."
            "<pre>[lyapunov]\nenabled = true\nrenormalize_dt = 0.1\ntransient = 5.0</pre>"
        )
    return f'<div class="analysis-report"><h2>Lyapunov Analysis</h2><p>{msg}</p></div>'


def _simulation_figures(df, config):
    time_var = "t"
    value_vars = [col for col in df.columns if col != time_var]
    figures = []

    plots_cfg = config.get("plots", {})
    ts_vars = plots_cfg.get("time_series", value_vars)
    max_vars_per_plot = config.get("max_vars_per_plot", 2)
    available_vars = set(df.columns)
    ts_vars = [v for v in ts_vars if v in available_vars]

    if len(ts_vars) > max_vars_per_plot:
        for i in range(0, len(ts_vars), max_vars_per_plot):
            figures.extend(plot_time_series(df, time_var, ts_vars[i:i + max_vars_per_plot]))
    else:
        figures.extend(plot_time_series(df, time_var, ts_vars))

    phase_cfgs = plots_cfg.get("phase", [])
    if not phase_cfgs:
        original_vars = config.get("variables", {}).get("names", [])
        if len(original_vars) in (2, 3):
            phase_cfgs = [{"vars": original_vars}]

    for cfg in phase_cfgs:
        vars_ = cfg["vars"]
        aspect = cfg.get("aspect", [1.0] * len(vars_))
        if not all(v in df.columns for v in vars_):
            continue
        if len(vars_) == 2:
            figures.append(plot_phase_2d(df, vars_[0], vars_[1], aspect))
        elif len(vars_) == 3:
            figures.append(plot_phase_3d(df, vars_[0], vars_[1], vars_[2], aspect))

    return figures


def main(model_name):
    csv_path = os.path.join("models", f"{model_name}.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Simulation CSV not found: {csv_path}. Run the generated Julia solver first."
        )

    df = pd.read_csv(csv_path)
    config = load_config(model_name)
    df = compute_derived_variables(df, config)

    sim_html = _figures_html(_simulation_figures(df, config))
    stability_html = _stability_content(model_name, config)
    lyapunov_html = _lyapunov_content(model_name, config)

    plots_cfg = config.get("plots", {})
    combine = bool(plots_cfg.get("combine_stability_lyapunov_plots", False))

    if combine:
        buttons = """
        <button onclick="showTab('sim')" class="active">Dynamics</button>
        <button onclick="showTab('analysis')">Stability &amp; Lyapunov</button>
        """
        tabs = f"""
        <div id="sim" class="tab-content active">{sim_html}</div>
        <div id="analysis" class="tab-content">
            <section class="analysis-section">{stability_html}</section>
            <section class="analysis-section">{lyapunov_html}</section>
        </div>
        """
    else:
        buttons = """
        <button onclick="showTab('sim')" class="active">Dynamics</button>
        <button onclick="showTab('stability')">Stability</button>
        <button onclick="showTab('lyapunov')">Lyapunov</button>
        """
        tabs = f"""
        <div id="sim" class="tab-content active">{sim_html}</div>
        <div id="stability" class="tab-content">{stability_html}</div>
        <div id="lyapunov" class="tab-content">{lyapunov_html}</div>
        """

    html_path = os.path.join("models", f"{model_name}.html")
    with open(html_path, "w") as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Model: {model_name}</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    body {{
        background: #000;
        color: #fff;
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 1.25rem 1.5rem 2.5rem;
    }}
    h1 {{ color: {TITLE_BLUE}; font-weight: 600; }}
    .tab-buttons {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem;
        margin: 0 0 1.2rem;
    }}
    .tab-buttons button {{
        appearance: none;
        background: {INACTIVE_TAB};
        color: white;
        border: 0;
        border-radius: 1px;
        padding: 0.65rem 1.15rem;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
        transition: background-color 120ms ease, transform 120ms ease;
    }}
    .tab-buttons button:hover {{ transform: translateY(-1px); }}
    .tab-buttons button.active {{ background: {ACTIVE_TAB}; }}
    .tab-content {{ display: none; }}
    .tab-content.active {{ display: block; }}
    .plot-container {{ width: 92%; margin: 0 auto 1rem; }}
    .analysis-report {{
        width: min(1100px, 92%);
        box-sizing: border-box;
        margin: 1rem auto 1.5rem;
        padding: 1rem 1.2rem;
        background: #111;
        color: #ddd;
        border-radius: 1px;
    }}
    .analysis-section + .analysis-section {{
        border-top: 1px solid #333;
        padding-top: 1.25rem;
        margin-top: 1.25rem;
    }}
    pre {{
        background: #222;
        color: #fff;
        padding: 1em;
        overflow-x: auto;
        border-radius: 4px;
    }}
    code {{ color: #d7ecff; }}
    table {{ border-collapse: collapse; }}
    th, td {{ border: 1px solid #555; padding: 0.35rem 0.55rem; }}
  </style>
</head>
<body>
  <div class="tab-buttons">{buttons}</div>
  <h1>Model: {model_name}</h1>
  {tabs}
  <script>
    function showTab(id) {{
      document.querySelectorAll('.tab-buttons button').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
      document.querySelector(`.tab-buttons button[onclick="showTab('${{id}}')"]`).classList.add('active');
      document.getElementById(id).classList.add('active');
      window.dispatchEvent(new Event('resize'));
    }}
  </script>
</body>
</html>
""")

    print(f"HTML report written to {html_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Plotly dynamics, stability and Lyapunov report tabs."
    )
    parser.add_argument("model_name", help="The model name, e.g. 'pendulum'.")
    args = parser.parse_args()
    main(args.model_name)
