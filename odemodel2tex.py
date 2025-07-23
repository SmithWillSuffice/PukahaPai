#!/usr/bin/env python3
'''
Generate LaTeX report for an ODE model from toml specs.

Update the global SUBS_DICT as needed for nicer math symbols.

Example Use:
-------------
Write your ODES toml model in `./models/`, e.g., 
```bash
./odemodel2tex.py models/mmt_base_1.toml --pdf
```

| Copyright: (c) 2025 Bijou M. Smith
| License: GNU General Public License v3.0 <https://www.gnu.org/licenses/gpl-3.0.html>
'''

# import os
# import argparse
# import toml
# import subprocess
# import re

# SUBS_DICT = {
#     'varphi': r'\varphi',
#     'alpha': r'\alpha',
#     'lambda': r'\lambda',
#     'Pi': r'\Pi',
#     'P': r'P',
#     'P_init': r'P_0',
#     'nu': r'\nu',
#     'Phi': r'\Phi',
#     'phi': r'\phi',
#     'gamma': r'\gamma',
#     'employment_gap': r'\Delta\lambda',
#     r'employment\_gap': r'\Delta\lambda',
#     '1.0': r'1',
#     'productive_Y': r'Y_r',
#     r'productive\_Y': r'Y_r',
#     'u': r'u',
#     'u_init': r'u_0',
#     'omega': r'\omega',
#     'jg_wage': r'w_j',
#     r'jg\_wage': r'w_j',
#     r'jg\_output': r'Y_j',
#     '*': r'',
#     r'\var\phi': r'\varphi',
#     r'\phi0': r'\phi_0',
# }

# def tex_escape(s):
#     return s.replace('_', r'\_')


# def substitute_symbols(expr, dotted=False):
#     # Handle derivative substitutions first
#     def repl_deriv(match):
#         var = match.group(1)
#         symbol = SUBS_DICT.get(var, var)
#         return f"\\dot{{{symbol}}}" if dotted else f"\\frac{{d{symbol}}}{{dt}}"

#     #expr = re.sub(r'\\bf_(\\w+)', repl_deriv, expr)
#     expr = re.sub(r'\bf_(\\w+)', repl_deriv, expr)

#     # Now replace other symbols
#     for key, val in sorted(SUBS_DICT.items(), key=lambda x: -len(x[0])):
#         #expr = re.sub(rf'\\b{re.escape(key)}\\b', val, expr)
#         expr = re.sub(rf'\b{re.escape(key)}\b', lambda m: val, expr)

#     expr = expr.replace('_', r'\_')
#     return expr

# def ode_lhs_tex(var, dotted=False):
#     if var.startswith("f_"):
#         symbol = SUBS_DICT.get(var[2:], var[2:])
#         return rf"\dot{{{symbol}}}" if dotted else rf"\frac{{d{symbol}}}{{dt}}"
#     return tex_escape(var)




# def generate_table(title, data):
#     lines = [r"\begin{table}[h]",
#              r"\centering",
#              rf"\caption{{{title}}}",
#              r"\begin{tabular}{lll}",
#              r"Name & Symbol & Value \\ \hline"]

#     for k, v in data.items():
#         name = tex_escape(k)
#         symbol = SUBS_DICT.get(k, k)
#         lines.append(f"{name} & ${symbol}$ & {v}" + r'\\ ')

#     lines.extend([r"\end{tabular}", r"\end{table}"])
#     return "\n".join(lines)

# def generate_equations_section(title, equations, dotted=False):
#     lines = [rf"\section*{{{title}}}", r"\begin{align*}"]
#     for k, v in equations.items():
#         lhs = ode_lhs_tex(k, dotted)
#         rhs = substitute_symbols(v, dotted)
#         lines.append(f"{lhs} &= {rhs} " + r'\\ ')
#     lines.append(r"\end{align*}")
#     return "\n".join(lines)



# def generate_latex(data, dotted=False):
#     lines = [r"\documentclass{article}",
#              r"\usepackage{amsmath}",
#              r"\usepackage[margin=1in]{geometry}",
#              r"\author{Bijou M. Smith}",
#              r"\title{ODE Model}",
#              r"\begin{document}",
#              r"\maketitle"]

#     if 'parameters' in data:
#         lines.append(generate_table("Parameters", data['parameters']))

#     if 'initial_conditions' in data:
#         lines.append(generate_table("Initial Conditions", data['initial_conditions']))

#     if 'equations' in data:
#         eqs = data['equations']
#         if 'auxiliary' in eqs:
#             lines.append(generate_equations_section("Auxiliary Equations", eqs['auxiliary'], dotted))
#         if 'ode' in eqs:
#             lines.append(generate_equations_section("ODE Equations", eqs['ode'], dotted))

#     lines.append(r"\end{document}")
#     return "\n".join(lines)



# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("input", help="Input TOML file")
#     parser.add_argument("--pdf", action="store_true", help="Compile to PDF")
#     parser.add_argument("dotted", action="store_true", help="Use dot notation for time derivatives")
#     args = parser.parse_args()

#     with open(args.input, "r") as f:
#         data = toml.load(f)

#     latex_code = generate_latex(data, dotted=args.dotted)

#     basename = os.path.splitext(os.path.basename(args.input))[0]
#     tex_file = os.path.join("docs", basename + ".tex")

#     os.makedirs("docs", exist_ok=True)
#     with open(tex_file, "w") as f:
#         f.write(latex_code)

#     print(f"LaTeX file written to: {tex_file}")

#     if args.pdf:
#         try:
#             subprocess.run(["pdflatex", basename + ".tex"], check=True, cwd="docs")
#             print("PDF compiled successfully.")
#         except subprocess.CalledProcessError:
#             print("Error running pdflatex. Please ensure it is installed.")

# if __name__ == "__main__":
#     main()

import os
import argparse
import toml
import subprocess
import re

SUBS_DICT = {
    'varphi': r'\varphi',
    'alpha': r'\alpha',
    'lambda': r'\lambda',
    'Pi': r'\Pi',
    'P': r'P',
    'P_init': r'P_0',
    'nu': r'\nu',
    'Phi': r'\Phi',
    'phi': r'\phi',
    'gamma': r'\gamma',
    'employment_gap': r'\Delta\lambda',
    '1.0': r'1',
    'productive_Y': r'Y_r',
    'jg_output': r'Y_j',
    'u': r'u',
    'u_init': r'u_0',
    'omega': r'\omega',
    'jg_wage': r'w_j',
    'phi0': r'\phi_0',
}

def tex_escape(s):
    return s.replace('_', r'\_')


def substitute_symbols(expr, dotted=False):
    # First handle f_variable references in RHS expressions
    def repl_f_var(match):
        var = match.group(1)
        symbol = SUBS_DICT.get(var, var)
        return f"\\dot{{{symbol}}}" if dotted else f"\\frac{{d{symbol}}}{{dt}}"
    
    # Replace f_variable patterns in the expression
    expr = re.sub(r'f_(\w+)', repl_f_var, expr)
    
    # Now replace other symbols first
    for key, val in sorted(SUBS_DICT.items(), key=lambda x: -len(x[0])):
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(key) + r'\b'
        # Escape backslashes in replacement string for regex
        escaped_val = val.replace('\\', '\\\\')
        expr = re.sub(pattern, escaped_val, expr)
    
    # Replace all multiplication patterns after symbol substitution
    expr = re.sub(r'\*\s*\(', r' \\cdot (', expr)  # * ( -> \cdot (
    expr = re.sub(r'\)\s*\*\s*([A-Za-z\\\\])', r') \\cdot \1', expr)  # ) * letter/fraction -> ) \cdot letter/fraction
    expr = re.sub(r'([A-Za-z])\s*\*\s*([A-Za-z\\\\])', r'\1 \\cdot \2', expr)  # letter * letter/fraction -> letter \cdot letter/fraction
    expr = re.sub(r'([A-Za-z])\s*\*\s*\\\\frac', r'\1 \\cdot \\\\frac', expr)  # letter * \frac -> letter \cdot \frac
    expr = re.sub(r'\)\s*\*\s*\\\\frac', r') \\cdot \\\\frac', expr)  # ) * \frac -> ) \cdot \frac
    
    # Remove any remaining standalone * operators
    expr = re.sub(r'\s*\*\s*', r' ', expr)
    
    # Sanity check: fix double backslashes that aren't newline commands
    # This handles cases where our regex escaping created \\lambda instead of \lambda
    expr = re.sub(r'\\\\(?!\\)', r'\\', expr)  # Replace \\ with \ but not \\\
    
    return expr


def ode_lhs_tex(var, dotted=False):
    if var.startswith("f_"):
        var_name = var[2:]  # Remove 'f_' prefix
        symbol = SUBS_DICT.get(var_name, var_name)
        return f"\\dot{{{symbol}}}" if dotted else f"\\frac{{d{symbol}}}{{dt}}"
    # For non-ODE variables, apply symbol substitution but don't escape underscores
    symbol = SUBS_DICT.get(var, var)
    return symbol


def generate_table(title, data):
    lines = [r"\begin{table}[h]",
             r"\centering",
             f"\\caption{{{title}}}",
             r"\begin{tabular}{lll}",
             r"Name & Symbol & Value \\ \hline " 
             r" &  &  \\[-10pt] " ]

    data_list = list(data.items())
    for i, (k, v) in enumerate(data_list):
        name = tex_escape(k)
        symbol = SUBS_DICT.get(k, k)
        # Add \\ only if not the last row
        ending = r' \\' if i < len(data_list) - 1 else ''
        lines.append(f"{name} & ${symbol}$ & {v}{ending}")

    lines.extend([r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def generate_equations_section(title, equations, dotted=False):
    lines = [f"\\section*{{{title}}}", r"\begin{align*}"]
    eq_list = list(equations.items())
    for i, (k, v) in enumerate(eq_list):
        lhs = ode_lhs_tex(k, dotted)
        rhs = substitute_symbols(v, dotted)
        # Add \\ only if not the last equation
        ending = r' \\' if i < len(eq_list) - 1 else ''
        lines.append(f"{lhs} &= {rhs}{ending}")
    lines.append(r"\end{align*}")
    return "\n".join(lines)


def generate_latex(data, name, dotted=False):
    lines = [r"\documentclass[12pt]{extarticle}",
             r"\usepackage{amsmath}",
             r"\usepackage[margin=1in]{geometry}",
             r"\author{Bijou M. Smith}",
             r"\title{ODE Model --- " + f'{name}' + " }",
             r"\begin{document}",
             r"\maketitle"]

    if 'parameters' in data:
        lines.append(generate_table("Parameters", data['parameters']))

    if 'initial_conditions' in data:
        lines.append(generate_table("Initial Conditions", data['initial_conditions']))

    if 'equations' in data:
        eqs = data['equations']
        if 'auxiliary' in eqs:
            lines.append(generate_equations_section("Auxiliary Equations", eqs['auxiliary'], dotted))
        if 'ode' in eqs:
            lines.append(generate_equations_section("ODE Equations", eqs['ode'], dotted))

    lines.append(r"\end{document}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input TOML file")
    parser.add_argument("--pdf", action="store_true", help="Compile to PDF")
    parser.add_argument("--dotted", action="store_true", help="Use dot notation for time derivatives")
    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = toml.load(f)

    name = data['model_name'].replace('_', ' ')
    
    latex_code = generate_latex(data, name, dotted=args.dotted)

    basename = os.path.splitext(os.path.basename(args.input))[0]
    tex_file = os.path.join("docs", basename + ".tex")

    os.makedirs("docs", exist_ok=True)
    with open(tex_file, "w") as f:
        f.write(latex_code)

    print(f"LaTeX file written to: {tex_file}")

    if args.pdf:
        try:
            subprocess.run(["pdflatex", basename + ".tex"], check=True, cwd="docs")
            print("PDF compiled successfully.")
        except subprocess.CalledProcessError:
            print("Error running pdflatex. Please ensure it is installed.")

if __name__ == "__main__":
    main()