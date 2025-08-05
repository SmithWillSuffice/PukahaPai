# -*- coding: utf-8 -*-
'''
stability
==========
A stability analysis utility that can be imported into plots4models.py
This includes loading the eigenvalue CSV, generating stability plots, 
and creating a report.

Copyright: (c) 2025 Bijou M. Smith
License: GNU General Public License v3.0 <https://www.gnu.org/licenses/gpl-
'''
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go


def load_eigenvalues(model_name):
    eig_csv = os.path.join("models", f"{model_name}_eigen.csv")
    if not os.path.exists(eig_csv):
        return None
    return pd.read_csv(eig_csv, header=None)


def safe_complex(x):
   try:
      s = str(x).strip()
      s = s.replace("−", "-")       # replace unicode minus
      s = s.replace(" ", "")        # remove all spaces
      s = s.replace("im", "j")      # convert Julia style to Python style
      return complex(s)
   except Exception:
      return complex("nan")


def safe_float(x):
    """
    Try to convert x to float safely.
    If it is a complex string, take the real part.
    If conversion fails, return nan.
    """
    try:
        c = safe_complex(x)
        return c.real
    except Exception:
        try:
            return float(x)
        except Exception:
            return float('nan')


def generate_stability_figures(eig_df):
    #t = eig_df.iloc[:, 0].round(1)  # str type I think
    t = pd.to_numeric(eig_df.iloc[:, 0], errors='coerce')

    eigvals = eig_df.iloc[:, 1:]

    max_real = eigvals.apply(lambda row: max(row.apply(lambda x: safe_complex(x).real)), axis=1)

    # 1. Max Re(λ)
    fig_max_real = go.Figure()
    fig_max_real.add_trace(go.Scatter(x=t, y=max_real, mode='lines', name='max Re(λ)'))
    fig_max_real.add_hline(y=0, line=dict(dash='dash', color='red'), annotation_text="Stability Threshold")

    fig_max_real.update_layout(
        title="Max Real Part of Eigenvalues Over Time",
        margin=dict(l=40, r=40, t=50, b=40),  # ⬅ reasonable margins
        xaxis=dict(
            title='t',
            #tickformat=".2f",  # ⬅ Enforce 3 decimal digits
            showgrid=True,
            gridcolor='rgba(100, 100, 100, 0.3)',
            zeroline=True,
            zerolinecolor='rgba(100, 100, 100, 0.5)',
            zerolinewidth=1
        ),
        yaxis=dict(
            title="max Re(λ)",
            showgrid=True,
            gridcolor='rgba(100, 100, 100, 0.3)',
            zeroline=True,
            zerolinecolor='rgba(100, 100, 100, 0.5)',
            zerolinewidth=1
        ),
        paper_bgcolor="black",
        plot_bgcolor="black",
        font=dict(color="white"),
        autosize=True,
        #height=400,
    )

    # 2. All Re(λᵢ)
    fig_reals = go.Figure()
    for col in eigvals.columns:
        eig_real = eigvals[col].apply(lambda x: safe_complex(x).real)
        fig_reals.add_trace(go.Scatter(x=t, y=eig_real, mode='lines', name=f"Re(λ{col})"))

    fig_reals.update_layout(
        title="Eigenvalue Real Parts Over Time",
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(
            title='t',
            #tickformat=".2f",
            showgrid=True,
            gridcolor='rgba(100, 100, 100, 0.3)',
            zeroline=True,
            zerolinecolor='rgba(100, 100, 100, 0.5)',
            zerolinewidth=1
        ),
        yaxis=dict(
            title="Re(λ)",
            showgrid=True,
            gridcolor='rgba(100, 100, 100, 0.3)',
            zeroline=True,
            zerolinecolor='rgba(100, 100, 100, 0.5)',
            zerolinewidth=1
        ),
        paper_bgcolor="black",
        plot_bgcolor="black",
        font=dict(color="white"),
        #height=400,
        autosize=True,
    )
    return [fig_max_real, fig_reals]




def generate_stability_report_md(model_name, eig_df):
    t_raw = eig_df.iloc[:, 0]
    eigvals = eig_df.iloc[:, 1:]
    
    # Convert time values to floats safely
    t = t_raw.apply(safe_float)
    
    # Compute max real part of eigenvalues at each timestep
    max_real = eigvals.apply(lambda row: max(row.apply(lambda x: safe_complex(x).real)), axis=1)
    
    report_lines = [
        f"# Stability Analysis for Model: `{model_name}`",
        "",
        f"**Simulation Time Range**: $t_0 = {t.iloc[0]:.3f}$ to $t_1 = {t.iloc[-1]:.3f}$",
        f"**Number of time steps**: {len(t)}",
        f"**Number of eigenvalues per timestep**: {eigvals.shape[1]}",
        ""
    ]
    
    if (max_real <= 0).all():
        report_lines += [
            "## ✅ The system remained stable throughout the entire simulation.",
            "All eigenvalues had negative real parts for the full duration."
        ]
    else:
        unstable_mask = max_real > 0
        unstable_times = t[unstable_mask]
        max_instability = max_real[unstable_mask]
        worst_index = max_instability.idxmax()
        worst_time = t.iloc[worst_index]
        worst_value = max_real.iloc[worst_index]
        
        # Find contiguous unstable regions
        unstable_intervals = []
        start = None
        for i in range(len(unstable_mask)):
            if unstable_mask.iloc[i]:
                if start is None:
                    start = t.iloc[i]
            elif start is not None:
                end = t.iloc[i-1]
                unstable_intervals.append((start, end))
                start = None
        if start is not None:
            unstable_intervals.append((start, t.iloc[-1]))
        
        report_lines += [
            "## ⚠️ Instability Detected",
            f"The system became unstable at **{len(unstable_times)}** time steps.",
            f"The worst instability occurred at $t = {worst_time:.3f}$ with $\\max\\ \\Re(\\lambda) = {worst_value:.3f}$.",
            "",
            f"### Unstable Periods",
        ]
        for i, (start, end) in enumerate(unstable_intervals, 1):
            duration = end - start
            report_lines.append(f"- Interval {i}: $t = {start:.3f}$ to $t = {end:.3f}$ (duration: {duration:.3f})")
        
        # Optional small table for a few instability snapshots
        if len(unstable_times) <= 10:
            report_lines += [
                "",
                "### Sample Instability Snapshots",
                "",
                "| Time $t$ | $\\max \\Re(\\lambda)$ |",
                "|----------|----------------------|"
            ]
            for t_val, max_val in zip(unstable_times, max_instability):
                report_lines.append(f"| {t_val:.3f} | {max_val:.3f} |")
    
    report_path = os.path.join("models", f"{model_name}_report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))
    return report_path



def generate_stability_report_html(model_name, eig_df):
    t_raw = eig_df.iloc[:, 0]
    eigvals = eig_df.iloc[:, 1:]
    
    t = t_raw.apply(safe_float)
    max_real = eigvals.apply(lambda row: max(row.apply(lambda x: safe_complex(x).real)), axis=1)
    
    html_lines = []
    
    html_lines.append(f"<h2>Stability Analysis for Model: <code style='font-size: 150%'>{model_name}</code></h2>")
    html_lines.append(f"<p><strong>Simulation Time Range:</strong> t₀ = {t.iloc[0]:.3f} to t₁ = {t.iloc[-1]:.3f}</p>")
    html_lines.append(f"<p><strong>Number of time steps:</strong> {len(t)}</p>")
    html_lines.append(f"<p><strong>Number of eigenvalues per timestep:</strong> {eigvals.shape[1]}</p>")
    
    if (max_real <= 0).all():
        html_lines.append("<h3 style='color: green;'>✅ The system remained stable throughout the entire simulation.</h3>")
        html_lines.append("<p>All eigenvalues had negative real parts for the full duration.</p>")
    else:
        unstable_mask = max_real > 0
        unstable_times = t[unstable_mask]
        max_instability = max_real[unstable_mask]
        worst_index = max_instability.idxmax()
        worst_time = t.iloc[worst_index]
        worst_value = max_real.iloc[worst_index]
        
        # Find contiguous unstable regions
        unstable_intervals = []
        start = None
        for i in range(len(unstable_mask)):
            if unstable_mask.iloc[i]:
                if start is None:
                    start = t.iloc[i]
            elif start is not None:
                end = t.iloc[i-1]
                unstable_intervals.append((start, end))
                start = None
        if start is not None:
            unstable_intervals.append((start, t.iloc[-1]))
        
        html_lines.append("<h3 style='color: orange;'>⚠️ Instability Detected</h3>")
        html_lines.append(f"<p>The system became unstable at <strong>{len(unstable_times)}</strong> time steps.</p>")
        html_lines.append(f"<p>The worst instability occurred at <strong>t = {worst_time:.3f}</strong> with <strong>max Re(λ) = {worst_value:.3f}</strong>.</p>")
        
        html_lines.append("<h3>Unstable Periods</h3>")
        html_lines.append("<ul>")
        for i, (start, end) in enumerate(unstable_intervals, 1):
            duration = end - start
            html_lines.append(f"<li>Interval {i}: t = {start:.3f} to t = {end:.3f} (duration: {duration:.3f})</li>")
        html_lines.append("</ul>")
        
        if len(unstable_times) <= 10:
            html_lines.append("<h4>Sample Instability Snapshots</h4>")
            html_lines.append("<table border='1' cellpadding='4' cellspacing='0'>")
            html_lines.append("<thead><tr><th>Time t</th><th>Max Re(λ)</th></tr></thead>")
            html_lines.append("<tbody>")
            for t_val, max_val in zip(unstable_times, max_instability):
                html_lines.append(f"<tr><td>{t_val:.3f}</td><td>{max_val:.3f}</td></tr>")
            html_lines.append("</tbody></table>")
    
    report_html = "\n".join(html_lines)
    
    report_path = os.path.join("models", f"{model_name}_report.html")
    with open(report_path, "w") as f:
        f.write(report_html)
    
    return report_path


# Export functions for use in plots4models.py
__all__ = ["load_eigenvalues", "generate_stability_figures", "generate_stability_report_html", ]

