#!/usr/bin/env python3
'''
generate_julia_odesolver.py
===========================
Generate command-line and GUI Julia solvers from a PukahaPai TOML model.

The TOML [solver].method setting is now honoured.  The special method IDA
selects a DAEProblem.  Any other simple DifferentialEquations.jl algorithm
constructor name (for example Tsit5, Vern7, Rodas5P, RK4) selects an
ODEProblem and is emitted as <method>().

Optional solver/output settings:

    [solver]
    dt = 0.01
    method = "Tsit5"
    adaptive = false
    output_dt = 0.05
    flush_every = 10
    abstol = 1e-8
    reltol = 1e-6

output_dt controls how often state data are written; it is independent of the
integration step.  flush_every applies to the streaming GUI writer.  The
command-line solver writes its saved solution after integration and therefore
does not flush on every row.

Copyright: (c) 2025-2026 Bijou M. Smith
License: GNU General Public License v3.0 <https://www.gnu.org/licenses/gpl-3.0.html>
'''

from collections import defaultdict, deque
from pathlib import Path
import re

from model_validation import ModelValidationError, load_and_validate_model


_SOLVER_NAME_RE = re.compile(r"^(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*(?:\(\))?$")


def julia_type(ctype_str):
    if ctype_str == "c_double":
        return "Float64"
    if ctype_str == "c_int":
        return "Int32"
    if ctype_str == "c_char":
        return "UInt8"
    raise ValueError(f"Unsupported ctype: {ctype_str}")


def parse_godley_flows(godley_section):
    flows = defaultdict(list)
    for key, entry in godley_section.items():
        if len(entry) < 4:
            raise ValueError(
                f"Godley table entry {key} must have 4 elements: "
                "[from, to, amount, desc]"
            )
        src, tgt, expr, _ = entry
        flows[src].append(f"-({expr})")
        flows[tgt].append(f"+({expr})")
    return flows


def get_dependencies(expr: str, all_eq_names: list) -> list:
    dependencies = []
    for eq_name in all_eq_names:
        if re.search(r"\b" + re.escape(eq_name) + r"\b", expr):
            dependencies.append(eq_name)
    return dependencies


def topological_sort(ode_equations: dict) -> list:
    graph = defaultdict(list)
    in_degree = defaultdict(int)
    all_eq_names = list(ode_equations.keys())

    for eq_name, expr in ode_equations.items():
        for dep in get_dependencies(expr, all_eq_names):
            if dep != eq_name:
                graph[dep].append(eq_name)
                in_degree[eq_name] += 1

    queue = deque([eq for eq in all_eq_names if in_degree[eq] == 0])
    sorted_equations = []

    while queue:
        node = queue.popleft()
        sorted_equations.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_equations) != len(ode_equations):
        raise ValueError("Circular dependency detected. Cannot sort.")

    return sorted_equations


def render_template(template: str, context: dict) -> str:
    from jinja2 import Template
    return Template(template).render(**context)


def substitute_expressions(expr: str, variable_names: list) -> str:
    """Substitute derivative variable names used inside other equations."""
    for var in variable_names:
        expr = re.sub(rf"\bd{var}\b", f"d{var}_dt", expr)
    return expr


def normalize_solver_method(method):
    """
    Return (constructor_expression, base_name).

    Model files specify a constructor name such as ``Tsit5`` or ``IDA``.
    A trailing empty ``()`` is accepted for convenience.  Dotted Julia names
    such as ``OrdinaryDiffEq.Tsit5`` are also accepted.  Arbitrary Julia code
    is rejected so a typo cannot silently become injected template source.
    """
    method = str(method).strip()
    if not _SOLVER_NAME_RE.fullmatch(method):
        raise ValueError(
            "[solver].method must be a Julia algorithm constructor name such "
            "as 'Tsit5', 'Rodas5P', 'RK4', or 'IDA'"
        )

    if method.endswith("()"):
        method = method[:-2]

    base_name = method.rsplit(".", 1)[-1]
    return f"{method}()", base_name


def _positive_float(section, name, default):
    value = float(section.get(name, default))
    if value <= 0.0:
        raise ValueError(f"[solver].{name} must be > 0")
    return value


def _positive_int(section, name, default):
    value = int(section.get(name, default))
    if value <= 0:
        raise ValueError(f"[solver].{name} must be a positive integer")
    return value


def generate_julia_code(model_name: str, template: str, gui_version: bool = False):
    model_dir = Path("models")
    toml_path = model_dir / f"{model_name}.toml"
    suffix = "_gui" if gui_version else "_cmdl"
    if not toml_path.exists():
        raise FileNotFoundError(f"Model file not found: {toml_path}")

    config = load_and_validate_model(toml_path)

    parameters = config.get("parameters", {})
    variable_names = config["variables"]["names"]
    init_vals = config["initial_conditions"]
    ode_equations_toml = config.get("equations", {}).get("ode", {})
    auxiliary_equations = config.get("equations", {}).get("auxiliary", {})
    godley_flows = config.get("godley", {})

    t0 = float(config["tspan"]["t0"])
    t1 = float(config["tspan"]["t1"])
    solver_config = config["solver"]
    dt = _positive_float(solver_config, "dt", 0.01)

    solver_constructor, solver_base_name = normalize_solver_method(
        solver_config.get("method", "Tsit5")
    )

    requested_problem_type = str(solver_config.get("problem_type", "")).strip().lower()
    if requested_problem_type and requested_problem_type not in {"ode", "dae"}:
        raise ValueError("[solver].problem_type must be 'ode' or 'dae'")

    if requested_problem_type:
        problem_type = requested_problem_type
    else:
        problem_type = "dae" if solver_base_name == "IDA" else "ode"

    solver_is_dae = problem_type == "dae"
    adaptive = bool(solver_config.get("adaptive", False))
    output_dt = _positive_float(solver_config, "output_dt", dt)
    flush_every = _positive_int(solver_config, "flush_every", 10)
    abstol = _positive_float(solver_config, "abstol", 1.0e-8)
    reltol = _positive_float(solver_config, "reltol", 1.0e-6)

    # Merge Godley flows into ode_equations, if any.
    ode_equations = ode_equations_toml.copy()
    godley_derivatives = parse_godley_flows(godley_flows)
    for varname, terms in godley_derivatives.items():
        eqname = f"f_{varname}"
        if eqname not in ode_equations:
            ode_equations[eqname] = " + ".join(terms)

    sorted_equation_names = topological_sort(ode_equations)

    derivative_computations = []
    for f_var_name in sorted_equation_names:
        expr = substitute_expressions(ode_equations[f_var_name], variable_names)
        derivative_computations.append((f_var_name, expr))

    aux_subst = {}
    for key, value in auxiliary_equations.items():
        aux_subst[key] = substitute_expressions(value, variable_names)

    # Every current TOML equation is an explicit state derivative.  The DAE
    # wrapper is therefore F(du,u,t) = du - f(u,t) when a DAE solver is chosen.
    missing_derivatives = [
        name for name in variable_names if f"f_{name}" not in ode_equations
    ]
    if missing_derivatives:
        raise ValueError(
            "No ODE/Godley derivative was generated for state variable(s): "
            + ", ".join(missing_derivatives)
        )

    differential_vars_list = ["true" for _ in variable_names]

    eigenvalue_config = config.get("eigenvalues", {})
    eigenvalue_enabled = bool(eigenvalue_config.get("all", False))
    eigenvalue_every_n_steps = int(eigenvalue_config.get("every_n_steps", 50))
    if eigenvalue_enabled and eigenvalue_every_n_steps <= 0:
        raise ValueError("[eigenvalues].every_n_steps must be a positive integer")

    lyapunov_config = config.get("lyapunov", {})
    lyapunov_enabled = bool(lyapunov_config.get("enabled", False))
    lyapunov_renormalize_dt = float(
        lyapunov_config.get("renormalize_dt", max(dt, 0.1))
    )
    lyapunov_transient = float(lyapunov_config.get("transient", 0.0))

    if lyapunov_enabled and lyapunov_renormalize_dt <= 0.0:
        raise ValueError("[lyapunov].renormalize_dt must be > 0")
    if lyapunov_enabled and lyapunov_transient < 0.0:
        raise ValueError("[lyapunov].transient must be >= 0")

    jacobian_enabled = eigenvalue_enabled or lyapunov_enabled

    context = {
        "model_name": model_name,
        "parameters": parameters,
        "variable_names": variable_names,
        "initial_conditions": init_vals,
        "derivative_computations": derivative_computations,
        "auxiliary_equations": aux_subst,
        "t0": t0,
        "t1": t1,
        "dt": dt,
        "output_dt": output_dt,
        "flush_every": flush_every,
        "adaptive": "true" if adaptive else "false",
        "abstol": abstol,
        "reltol": reltol,
        "solver_constructor": solver_constructor,
        "solver_base_name": solver_base_name,
        "problem_type": problem_type,
        "solver_is_dae": solver_is_dae,
        "variable_count": len(variable_names),
        "differential_vars_list": differential_vars_list,
        "eigenvalue_enabled": eigenvalue_enabled,
        "eigenvalue_every_n_steps": eigenvalue_every_n_steps,
        "lyapunov_enabled": lyapunov_enabled,
        "lyapunov_renormalize_dt": lyapunov_renormalize_dt,
        "lyapunov_transient": lyapunov_transient,
        "jacobian_enabled": jacobian_enabled,
    }

    julia_code = render_template(template, context)
    outpath = model_dir / f"{model_name}{suffix}.jl"
    outpath.write_text(julia_code)
    print(
        f"Wrote Julia code to: {outpath} "
        f"({problem_type.upper()}Problem, {solver_constructor})"
    )
    return outpath


def main():
    import sys

    if len(sys.argv) != 2:
        print("Usage: python3 generate_julia_odesolver.py <model_name>")
        return 1

    gui_template_path = Path("templates/ode_dae_solver_gui.jl.template")
    cmdl_template_path = Path("templates/ode_dae_solver_cmdl.jl.template")
    model_name = sys.argv[1]

    try:
        generate_julia_code(
            model_name, gui_template_path.read_text(), gui_version=True
        )
        generate_julia_code(
            model_name, cmdl_template_path.read_text(), gui_version=False
        )
    except ModelValidationError as exc:
        print()
        print(exc)
        print("No Julia solver was generated.")
        return 2

    print(f"Generated GUI and standalone Julia solvers for model: {model_name}")
    print(f"Run standalone with: julia models/{model_name}_cmdl.jl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
