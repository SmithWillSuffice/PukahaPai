#!/usr/bin/env python3
'''
generate_julia_odesolver.py
===========================
This script generates a Julia ODE solver script based on a TOML configuration
file. It reads the model configuration from toml config, extracts parameters,
variables, and equations, and renders a Julia script using a Jinja-like
template.

Example:
```bash
./generate_julia_odesolver.py pendulum
```
This presumes an ODES model specification `pendulum.toml` exists in
the `./models` directory. If successful, the generated Julia code will be
in `./models/pendulum.jl`. Another cmdl only version will be generated
as `./models/pendulum_cmdl.jl`.

| Copyright: (c) 2025 Bijou M. Smith
| License: GNU General Public License v3.0 <https://www.gnu.org/licenses/gpl-3.0.html>
'''
# FLAGGED - This is the final, corrected version of the Python script.

from pathlib import Path
import tomllib
import re
from collections import defaultdict, deque

def julia_type(ctype_str):
    if ctype_str == "c_double":
        return "Float64"
    elif ctype_str == "c_int":
        return "Int32"
    elif ctype_str == "c_char":
        return "UInt8"
    else:
        raise ValueError(f"Unsupported ctype: {ctype_str}")

def parse_godley_flows(godley_section):
    flows = defaultdict(list)
    for key, entry in godley_section.items():
        if len(entry) < 4:
            raise ValueError(f"Godley table entry {key} must have 4 elements: [from, to, amount, desc]")
        src, tgt, expr, _ = entry
        flows[src].append(f"-({expr})")
        flows[tgt].append(f"+({expr})")
    return flows

def get_dependencies(expr: str, all_eq_names: list) -> list:
    """
    Finds which derivative equations an expression depends on.
    Uses a more robust regex to find 'f_' prefixed variable names.
    """
    dependencies = []
    for eq_name in all_eq_names:
        # Use regex to find the equation name as a whole word
        if re.search(r'\b' + re.escape(eq_name) + r'\b', expr):
            dependencies.append(eq_name)
    return dependencies

def topological_sort(ode_equations: dict) -> list:
    """
    Sorts ODE equations based on dependencies to prevent UndefVarError.
    This implementation is more robust and correctly handles complex dependencies.
    """
    graph = defaultdict(list)
    in_degree = defaultdict(int)
    all_eq_names = list(ode_equations.keys())

    # Build the dependency graph and compute in-degrees
    for eq_name, expr in ode_equations.items():
        dependencies = get_dependencies(expr, all_eq_names)
        for dep in dependencies:
            if dep != eq_name:
                graph[dep].append(eq_name)
                in_degree[eq_name] += 1

    # Initialize a queue with all nodes that have no incoming edges
    queue = deque([eq for eq in all_eq_names if in_degree[eq] == 0])
    sorted_equations = []

    # Perform the topological sort
    while queue:
        node = queue.popleft()
        sorted_equations.append(node)

        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # Check for cycles
    if len(sorted_equations) != len(ode_equations):
        # This means there's a circular dependency.
        raise ValueError("Circular dependency detected. Cannot sort.")

    return sorted_equations

def render_template(template: str, context: dict) -> str:
    from jinja2 import Template
    return Template(template).render(**context)

def substitute_expressions(expr: str, variable_names: list) -> str:
    """Substitutes derivative variable names."""
    for var in variable_names:
        expr = re.sub(rf'\bd{var}\b', f'd{var}_dt', expr)
    return expr

def generate_julia_code(model_name: str, template: str, gui_version: bool = False):
    model_dir = Path("models")
    toml_path = model_dir / f"{model_name}.toml"
    suffix = "_gui" if gui_version else "_cmdl"
    if not toml_path.exists():
        raise FileNotFoundError(f"Model file not found: {toml_path}")

    with open(toml_path, "rb") as f:
        config = tomllib.load(f)

    parameters = config.get("parameters", {})
    variable_names = config["variables"]["names"]
    init_vals = config["initial_conditions"]
    ode_equations_toml = config.get("equations", {}).get("ode", {})
    auxiliary_equations = config.get("equations", {}).get("auxiliary", {})
    godley_flows = config.get("godley", {})

    t0 = config["tspan"]["t0"]
    t1 = config["tspan"]["t1"]
    dt = config["solver"]["dt"]
    method = config["solver"].get("method", "Tsit5")

    # Merge Godley flows into ode_equations, if any
    ode_equations = ode_equations_toml.copy()
    godley_derivatives = parse_godley_flows(godley_flows)
    for varname, terms in godley_derivatives.items():
        eqname = f"f_{varname}"
        if eqname not in ode_equations:
            ode_equations[eqname] = " + ".join(terms)

    # Sort equations topologically to ensure dependencies are met
    try:
        sorted_equation_names = topological_sort(ode_equations)
    except ValueError as e:
        raise e

    # Prepare derivative computations for the template
    derivative_computations = []
    for f_var_name in sorted_equation_names:
        original_var = f_var_name[2:]
        expr = substitute_expressions(ode_equations[f_var_name], variable_names)
        derivative_computations.append((f_var_name, expr))

    # Prepare auxiliary equations
    aux_subst = {}
    for k, v in auxiliary_equations.items():
        expr = substitute_expressions(v, variable_names)
        aux_subst[k] = expr

    # Generate the list of boolean values for differential_vars
    differential_vars_list = ["true" for _ in variable_names]

    context = {
        "model_name": config["model_name"],
        "parameters": parameters,
        "variable_names": variable_names,
        "initial_conditions": init_vals,
        "derivative_computations": derivative_computations,
        "auxiliary_equations": aux_subst,
        "t0": t0,
        "t1": t1,
        "dt": dt,
        "method": method,
        "variable_count": len(variable_names),
        "differential_vars_list": differential_vars_list,
    }

    julia_code = render_template(template, context)
    outpath = model_dir / f"{model_name}{suffix}.jl"
    with open(outpath, "w") as f:
        f.write(julia_code)
    print(f"Wrote Julia code to: {outpath}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python3 generate_julia_odesolver.py <model_name>")
        sys.exit(1)

    TEMPLATE_1_PATH = "./templates/ode_dae_solver_gui.jl.template"
    TEMPLATE_2_PATH = "./templates/ode_dae_solver_cmdl.jl.template"

    model_name = sys.argv[1]

    with open(TEMPLATE_1_PATH, 'r') as f:
        gui_template = f.read()
        generate_julia_code(model_name, gui_template, gui_version=True)

    with open(TEMPLATE_2_PATH, 'r') as f:
        standalone_template = f.read()
        generate_julia_code(model_name, standalone_template, gui_version=False)

    print(f"Generated GUI and standalone Julia DAE solvers for model: {model_name}")
    print(f"Run standalone with: julia models/{model_name}_cmdl.jl")
