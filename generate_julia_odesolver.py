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
###
### OLD: was doing dopey full expr substitution in the DE's.
###
# from pathlib import Path
# import tomllib
# import re
# from collections import defaultdict

# def julia_type(ctype_str):
#     if ctype_str == "c_double":
#         return "Float64"
#     elif ctype_str == "c_int":
#         return "Int32"
#     elif ctype_str == "c_char":
#         return "UInt8"
#     else:
#         raise ValueError(f"Unsupported ctype: {ctype_str}")

# def generate_julia_struct(model_name, param_dict):
#     fields = ["    state::UInt8", "    t0::Float64", "    t1::Float64"]
#     for name in param_dict.keys():
#         fields.append(f"    {name}::Float64")

#     struct_code = f'''
# # Auto-generated struct for shared memory interop
# struct {model_name}_Shared
# {chr(10).join(fields)}
# end

# function open_shared_{model_name}()
#     shmpath = "/dev/shm/pukaha_shared"
#     sz = sizeof({model_name}_Shared)
#     if !isfile(shmpath)
#         error("Shared memory file not found - is the GUI controller running?")
#     elseif filesize(shmpath) != sz
#         error("Shared memory size mismatch - please restart the GUI")
#     end
#     fd = nothing
#     try
#         fd = open(shmpath, "r+")
#         arr = Mmap.mmap(fd, Vector{UInt8}, sz)
#         return arr, Ptr{{{model_name}_Shared}}(pointer(arr))
#     catch e
#         fd !== nothing && close(fd)
#         rethrow(e)
#     end
# end

# function read_shared_params()
#     arr, ptr = open_shared_{model_name}()
#     try
#         return unsafe_load(ptr)
#     finally
#         finalize(arr)
#     end
# end

# function write_shared_state(new_state::Char)
#     arr, ptr = open_shared_{model_name}()
#     try
#         unsafe_store!(Ptr{UInt8}(pointer(arr)), UInt8(new_state))
#     finally
#         finalize(arr)
#     end
# end

# function check_gui_state()
#     arr, ptr = open_shared_{model_name}()
#     try
#         state_byte = unsafe_load(Ptr{UInt8}(pointer(arr)))
#         return Char(state_byte)
#     finally
#         finalize(arr)
#     end
# end
# '''
#     return struct_code

# def resolve_derivative_references(ode_equations, variable_names):
#     resolved_equations = {}
#     derivative_refs = {}
#     for eq_name, equation in ode_equations.items():
#         refs = re.findall(r'f_(\w+)', equation)
#         derivative_refs[eq_name] = refs

#     f_name_to_equation = {k: v for k, v in ode_equations.items()}

#     for eq_name, equation in ode_equations.items():
#         resolved = equation
#         for ref in derivative_refs[eq_name]:
#             f_ref = f"f_{ref}"
#             if f_ref in f_name_to_equation:
#                 resolved = resolved.replace(f_ref, f"({f_name_to_equation[f_ref]})")
#             else:
#                 raise ValueError(f"Reference to undefined derivative: {f_ref}")
#         resolved_equations[eq_name] = resolved
#     return resolved_equations

# def parse_godley_flows(godley_section):
#     flows = defaultdict(list)
#     for key, entry in godley_section.items():
#         if len(entry) < 4:
#             raise ValueError(f"Godley table entry {key} must have 4 elements: [from, to, amount, desc]")
#         src, tgt, expr, _ = entry
#         flows[src].append(f"-({expr})")
#         flows[tgt].append(f"+({expr})")
#     return flows

# def render_template(template: str, context: dict) -> str:
#     from jinja2 import Template
#     return Template(template).render(**context)

# def generate_julia_code(model_name: str, template: str, gui_version: bool = True):
#     model_dir = Path("models")
#     toml_path = model_dir / f"{model_name}.toml"
#     suffix = "_gui" if gui_version else "_cmdl"
#     if not toml_path.exists():
#         raise FileNotFoundError(f"Model file not found: {toml_path}")

#     with open(toml_path, "rb") as f:
#         config = tomllib.load(f)

#     parameters = config.get("parameters", {})
#     variable_names = config["variables"]["names"]
#     init_vals = config["initial_conditions"]    
#     ode_equations = config.get("equations", {}).get("ode", {})
#     auxiliary_equations = config.get("equations", {}).get("auxiliary", {})
#     godley_flows = config.get("godley", {})

#     t0 = config["tspan"]["t0"]
#     t1 = config["tspan"]["t1"]
#     dt = config["solver"]["dt"]
#     method = config["solver"].get("method", "Tsit5")

#     godley_derivatives = parse_godley_flows(godley_flows)
#     for varname, terms in godley_derivatives.items():
#         eqname = f"f_{varname}"
#         if eqname not in ode_equations:
#             ode_equations[eqname] = " + ".join(terms)

#     resolved_ode_equations = resolve_derivative_references(ode_equations, variable_names)

#     equation_ordered = []
#     for i, name in enumerate(variable_names):
#         eq_name = f"f_{name}"
#         if eq_name in resolved_ode_equations:
#             equation_ordered.append((eq_name, resolved_ode_equations[eq_name]))
#         else:
#             raise ValueError(f"Missing ODE for variable: {name}")

#     context = {
#         "model_name": config["model_name"],
#         "parameters": parameters,
#         "variable_names": variable_names,
#         "initial_conditions": init_vals,
#         "ode_equations": {k: v for k, v in equation_ordered},
#         "auxiliary_equations": auxiliary_equations,
#         "t0": t0,
#         "t1": t1,
#         "dt": dt,
#         "method": method,
#         "variable_count": len(variable_names),
#     }

#     if gui_version:
#         context["julia_struct_code"] = generate_julia_struct(model_name, parameters)

#     julia_code = render_template(template, context)
#     outpath = model_dir / f"{model_name}{suffix}.jl"
#     with open(outpath, "w") as f:
#         f.write(julia_code)

#     print(f"Wrote Julia code to: {outpath}")

     


# if __name__ == "__main__":
#     import sys
#     if len(sys.argv) != 2:
#         print("Usage: python3 generate_julia_odesolver.py <model_name>")
#         sys.exit(1)

#     TEMPLATE_1_PATH = Path(__file__).parent / "templates" / "ode_simsolver.jl.template"
#     TEMPLATE_2_PATH = "./templates/ode_simsolver_cmdl.jl.template"

#     model_name = sys.argv[1]

#     with open(TEMPLATE_1_PATH, 'r') as f:
#         gui_template = f.read()
#         generate_julia_code(model_name, gui_template)

#     with open(TEMPLATE_2_PATH, 'r') as f:
#         standalone_template = f.read()
#         generate_julia_code(model_name, standalone_template, gui_version=False)

#     print(f"Generated GUI and standalone Julia ODE solvers for model: {model_name}")
#     print(f"Run standalone with: julia models/{model_name}_cmdl.jl")


from pathlib import Path
import tomllib
import re
from collections import defaultdict


def julia_type(ctype_str):
    if ctype_str == "c_double":
        return "Float64"
    elif ctype_str == "c_int":
        return "Int32"
    elif ctype_str == "c_char":
        return "UInt8"
    else:
        raise ValueError(f"Unsupported ctype: {ctype_str}")

def generate_julia_struct(model_name, param_dict):
    fields = ["    state::UInt8", "    t0::Float64", "    t1::Float64"]
    for name in param_dict.keys():
        fields.append(f"    {name}::Float64")

    struct_code = f'''
# Auto-generated struct for shared memory interop
struct {model_name}_Shared
{chr(10).join(fields)}
end

function open_shared_{model_name}()
    shmpath = "/dev/shm/pukaha_shared"
    sz = sizeof({model_name}_Shared)
    if !isfile(shmpath)
        error("Shared memory file not found - is the GUI controller running?")
    elseif filesize(shmpath) != sz
        error("Shared memory size mismatch - please restart the GUI")
    end
    fd = nothing
    try
        fd = open(shmpath, "r+")
        arr = Mmap.mmap(fd, Vector{{UInt8}}, sz)
        return arr, Ptr{{{model_name}_Shared}}(pointer(arr))
    catch e
        fd !== nothing && close(fd)
        rethrow(e)
    end
end

function read_shared_params()
    arr, ptr = open_shared_{model_name}()
    try
        return unsafe_load(ptr)
    finally
        finalize(arr)
    end
end

function write_shared_state(new_state::Char)
    arr, ptr = open_shared_{model_name}()
    try
        unsafe_store!(Ptr{{UInt8}}(pointer(arr)), UInt8(new_state))
    finally
        finalize(arr)
    end
end

function check_gui_state()
    arr, ptr = open_shared_{model_name}()
    try
        state_byte = unsafe_load(Ptr{{UInt8}}(pointer(arr)))
        return Char(state_byte)
    finally
        finalize(arr)
    end
end
'''
    return struct_code


# REMOVED THIS FUNCTION - we don't want to resolve references anymore
# def resolve_derivative_references(ode_equations, variable_names):
#     # This function was expanding f_P, f_lambda etc. into full expressions
#     # We want to keep them as variable references instead


def parse_godley_flows(godley_section):
    flows = defaultdict(list)
    for key, entry in godley_section.items():
        if len(entry) < 4:
            raise ValueError(f"Godley table entry {key} must have 4 elements: [from, to, amount, desc]")
        src, tgt, expr, _ = entry
        flows[src].append(f"-({expr})")
        flows[tgt].append(f"+({expr})")
    return flows


def render_template(template: str, context: dict) -> str:
    from jinja2 import Template
    return Template(template).render(**context)


def generate_julia_code(model_name: str, template: str, gui_version: bool = True):
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
    ode_equations = config.get("equations", {}).get("ode", {})
    auxiliary_equations = config.get("equations", {}).get("auxiliary", {})
    godley_flows = config.get("godley", {})

    t0 = config["tspan"]["t0"]
    t1 = config["tspan"]["t1"]
    dt = config["solver"]["dt"]
    method = config["solver"].get("method", "Tsit5")

    godley_derivatives = parse_godley_flows(godley_flows)
    for varname, terms in godley_derivatives.items():
        eqname = f"f_{varname}"
        if eqname not in ode_equations:
            ode_equations[eqname] = " + ".join(terms)

    # REMOVED: resolved_ode_equations = resolve_derivative_references(ode_equations, variable_names)
    # Use ode_equations directly instead

    equation_ordered = []
    for i, name in enumerate(variable_names):
        eq_name = f"f_{name}"
        if eq_name in ode_equations:  # Use ode_equations instead of resolved_ode_equations
            equation_ordered.append((eq_name, ode_equations[eq_name]))  # Use original equations
        else:
            raise ValueError(f"Missing ODE for variable: {name}")

    context = {
        "model_name": config["model_name"],
        "parameters": parameters,
        "variable_names": variable_names,
        "initial_conditions": init_vals,
        "ode_equations": {k: v for k, v in equation_ordered},
        "auxiliary_equations": auxiliary_equations,
        "t0": t0,
        "t1": t1,
        "dt": dt,
        "method": method,
        "variable_count": len(variable_names),
    }

    if gui_version:
        context["julia_struct_code"] = generate_julia_struct(model_name, parameters)

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

    TEMPLATE_1_PATH = Path(__file__).parent / "templates" / "ode_simsolver.jl.template"
    TEMPLATE_2_PATH = "./templates/ode_simsolver_cmdl.jl.template"

    model_name = sys.argv[1]

    with open(TEMPLATE_1_PATH, 'r') as f:
        gui_template = f.read()
        generate_julia_code(model_name, gui_template)

    with open(TEMPLATE_2_PATH, 'r') as f:
        standalone_template = f.read()
        generate_julia_code(model_name, standalone_template, gui_version=False)

    print(f"Generated GUI and standalone Julia ODE solvers for model: {model_name}")
    print(f"Run standalone with: julia models/{model_name}_cmdl.jl")