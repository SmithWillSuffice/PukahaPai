#!/usr/bin/env python3
'''
godley_check
============

Runs preprocessing check to ensure suspect Godley Tables in a `./model/*.toml`
file is ok. The user has to manually inspect the generated output to tell 
if the Godley Table is as they desire.

This script only generates a tabular output.

| Copyright: (c) 2025 Bijou M. Smith
| License: GNU General Public License v3.0  <https://www.gnu.org/licenses/gpl-3.0.html>
'''
import sys
import toml
import pandas as pd
import subprocess
from pathlib import Path
import re

DOCS_DIR = Path('./docs')
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def parse_godley_table(toml_path):
    data = toml.load(toml_path)
    godley = data.get("godley", {})

    transactions = []
    accounts = set()

    for tid, entry in godley.items():
        from_acct, to_acct, amount, desc = entry
        transactions.append({
            "desc": desc,
            "from": from_acct,
            "to": to_acct,
            "amount": amount
        })
        accounts.add(from_acct)
        accounts.add(to_acct)

    return sorted(accounts), transactions


def make_godley_df(accounts, transactions):
    df = pd.DataFrame(columns=["Description"] + accounts)

    for tx in transactions:
        row = {acct: "-" for acct in accounts}
        row["Description"] = tx["desc"]
        row[tx["from"]] = f"-{tx['amount']}"
        row[tx["to"]] = tx["amount"]
        df.loc[len(df)] = row

    return df


def write_markdown(df, out_path):
    with open(out_path, "w") as f:
        f.write(df.to_markdown(index=False))


def latex_symbol_subs(expr: str, cdots=False ) -> str:
    subs = {
        'lambda': r'\\lambda',
        'alpha': r'\\alpha',
        'beta': r'\\beta',
        'theta': r'\\theta',
        'pi': r'\\pi',
        'gamma': r'\\gamma',
    }

    # First pass: safe substitutions using word boundaries
    for k, v in subs.items():
        expr = re.sub(rf'\b{re.escape(k)}\b', v, expr)

    # Second pass: convert remaining * into \cdot
    expr = expr.replace('*', r'\cdot ')
    if not cdots:
        expr = expr.replace(r'\cdot', r' ')

    return expr


def write_tex(df, model_name):
    def texify_cell(cell):
        if cell.strip() == '-' or not cell:
            return '-'
        return f"${latex_symbol_subs(cell)}$"

    def texify_header(header):
        if header == 'Description':
            return 'Description'
        return f"${header}$"  # Use math mode for account headers like F_D

    headers = [texify_header(col) for col in df.columns]
    rows = []

    for _, row in df.iterrows():
        row_str = ' & '.join(
            [row['Description']] + [texify_cell(str(row[col])) for col in df.columns[1:]]
        ) + r" \\"
        rows.append(row_str)

    table = '\n'.join(rows)
    column_align = 'l' + 'c' * (len(headers) - 1)

    model_name_tex = model_name.replace(r'_', r'\_')

    tex = rf"""
%% For just the table in landscape
%\documentclass[a4paper]{{article}}
%\usepackage[margin=1in]{{geometry}}
%\usepackage{{booktabs}}
%\usepackage{{pdflscape}}  % or lscape

%% for whoel doc in landscape
\documentclass[a4paper,landscape]{{article}}
\usepackage{{booktabs}}
\usepackage[margin=1in]{{geometry}}


\begin{{document}}

\subsection*{{Godley Table for model: {model_name_tex} }}

%%\begin{{landscape}}
\begin{{tabular}}{{{column_align}}}
\toprule
{' & '.join(headers)} \\\\
\midrule
{table}
\bottomrule
\end{{tabular}}
%%\end{{landscape}}

\end{{document}}
"""

    tex_path = DOCS_DIR / f"{model_name}_godley.tex"
    with open(tex_path, 'w') as f:
        f.write(tex.strip())
    print(f"Wrote LaTeX source to: {tex_path}")
    return tex_path


def compile_pdf(tex_path):
    print(f"Compiling PDF in './docs/' ...")
    subprocess.run([
        "pdflatex",
        "-interaction=nonstopmode",
        "-output-directory", str(DOCS_DIR),
        str(tex_path)
    ], check=True)
    print(f"PDF written to: {tex_path.with_suffix('.pdf')}")




def main():
    if len(sys.argv) != 2:
        print("Usage: godley_check.py <model_basename>")
        sys.exit(1)

    basename = sys.argv[1]
    model_path = Path(f"./models/{basename}.toml")
    md_path = Path(f"{DOCS_DIR}/{basename}_godley.md")
    tex_path = Path(f"{DOCS_DIR}/{basename}_godley.tex")
    pdf_path = tex_path.with_suffix(".pdf")

    if not model_path.exists():
        print(f"Error: File not found: {model_path}")
        sys.exit(1)

    accounts, transactions = parse_godley_table(model_path)
    df = make_godley_df(accounts, transactions)

    print(f"Parsed {len(transactions)} Godley entries with {len(accounts)} accounts")
    print(df)

    write_markdown(df, md_path)
    write_tex(df, basename)
    compile_pdf(tex_path)

    print(f"\nMarkdown written to: {md_path}")
    print(f"PDF written to: {pdf_path}")


if __name__ == "__main__":
    main()
