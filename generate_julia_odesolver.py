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



# from pathlib import Path
# import tomllib 


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
#     """Generate Julia struct that matches Python SharedSimState exactly"""
#     fields = ["    state::UInt8"]
#     fields.append("    t0::Float64")     # ODES start time
#     fields.append("    t1::Float64")     # ODES stop time
    
#     # Add all parameters in same order as Python
#     for name in param_dict.keys():
#         fields.append(f"    {name}::Float64")
    
# def generate_julia_struct(model_name, param_dict):
#     fields = ["    state::UInt8"]
#     fields.append("    t0::Float64")
#     fields.append("    t1::Float64")
    
#     for name in param_dict.keys():
#         fields.append(f"    {name}::Float64")
    
#     # Use double braces for Julia's single braces, and triple for template variables
#     struct_code = f'''
# # Auto-generated struct for shared memory interop
# struct {model_name}_Shared
# {chr(10).join(fields)}
# end

# function open_shared_{model_name}()
#     shmpath = "/dev/shm/pukaha_shared"
#     sz = sizeof({model_name}_Shared)
    
#     # Verify shared memory exists and has correct size
#     if !isfile(shmpath)
#         error("Shared memory file not found - is the GUI controller running?")
#     elseif filesize(shmpath) != sz
#         error("Shared memory size mismatch - please restart the GUI")
#     end
    
#     # Open with proper error handling
#     fd = nothing
#     try
#         fd = open(shmpath, "r+")
#         arr = Mmap.mmap(fd, Vector{{UInt8}}, sz)
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
#         finalize(arr)  # Clean up memory mapping
#     end
# end

# function write_shared_state(new_state::Char)
#     arr, ptr = open_shared_{model_name}()
#     try
#         unsafe_store!(Ptr{{UInt8}}(pointer(arr)), UInt8(new_state))
#     finally
#         finalize(arr)
#     end
# end

# function check_gui_state()
#     arr, ptr = open_shared_{model_name}()
#     try
#         state_byte = unsafe_load(Ptr{{UInt8}}(pointer(arr)))
#         return Char(state_byte)
#     finally
#         finalize(arr)
#     end
# end
# '''
#     return struct_code


# def render_template(template: str, context: dict) -> str:
#     """Render a Jinja2 template with the given context."""
#     try:
#         from jinja2 import Template
#     except ImportError:
#         raise ImportError("You need to install jinja2: pip install jinja2")
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

#     t0 = config["tspan"]["t0"]
#     t1 = config["tspan"]["t1"]
#     dt = config["solver"]["dt"]
#     method = config["solver"].get("method", "Tsit5")

#     context = {
#         "model_name": config["model_name"],
#         "parameters": parameters,
#         "variable_names": variable_names,
#         "initial_conditions": init_vals,
#         "ode_equations": ode_equations,
#         "t0": t0,
#         "t1": t1,
#         "dt": dt,
#         "method": method,
#         "variable_count": len(variable_names),
#     }
#     if auxiliary_equations is not None:
#         context["auxiliary_equations"] = auxiliary_equations

#     # For index consistency:
#     equation_ordered = []
#     for i, name in enumerate(variable_names):
#         eq_name = f"f_{name}"
#         if eq_name in ode_equations:
#             equation_ordered.append((eq_name, ode_equations[eq_name]))
#         else:
#             raise ValueError(f"Missing ODE for variable: {name}")
#     context["ode_equations"] = {k: v for k, v in equation_ordered}


#     # Only include struct code for GUI version
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
#     #TEMPLATE_2_PATH = Path(__file__).parent / "templates" / "ode_simsolver_cmdl.jl.template"
#     TEMPLATE_2_PATH = "./templates/ode_simsolver_cmdl.jl.template"
    
#     model_name = sys.argv[1]
#     # Read and process GUI template
#     with open(TEMPLATE_1_PATH, 'r') as f:
#         gui_template = f.read()
#         generate_julia_code(model_name, gui_template)
    
#     # Read and process standalone template
#     with open(TEMPLATE_2_PATH, 'r') as f:
#         standalone_template = f.read()
#         generate_julia_code(model_name, standalone_template, gui_version=False)
#         #print(f"Read in template: {standalone_template}")
    
#     print(f"Generated GUI and standalone Julia ODE solvers for model: {model_name}")
#     print("You can now use a GUI controller, or run standalone:")
#     print(f"julia models/{model_name}_cmdl.jl")

from pathlib import Path
import tomllib 
import re


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
    """Generate Julia struct that matches Python SharedSimState exactly"""
    fields = ["    state::UInt8"]
    fields.append("    t0::Float64")     # ODES start time
    fields.append("    t1::Float64")     # ODES stop time
    
    # Add all parameters in same order as Python
    for name in param_dict.keys():
        fields.append(f"    {name}::Float64")
    
    # Use double braces for Julia's single braces, and triple for template variables
    struct_code = f'''
# Auto-generated struct for shared memory interop
struct {model_name}_Shared
{chr(10).join(fields)}
end

function open_shared_{model_name}()
    shmpath = "/dev/shm/pukaha_shared"
    sz = sizeof({model_name}_Shared)
    
    # Verify shared memory exists and has correct size
    if !isfile(shmpath)
        error("Shared memory file not found - is the GUI controller running?")
    elseif filesize(shmpath) != sz
        error("Shared memory size mismatch - please restart the GUI")
    end
    
    # Open with proper error handling
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
        finalize(arr)  # Clean up memory mapping
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


def resolve_derivative_references(ode_equations, variable_names):
    """
    Resolve references to other derivatives (f_varname) in ODE equations.
    This handles cases where one derivative equation references another derivative.
    """
    resolved_equations = {}
    
    # First pass: identify all derivative references
    derivative_refs = {}
    for eq_name, equation in ode_equations.items():
        # Find all f_varname patterns
        refs = re.findall(r'f_(\w+)', equation)
        derivative_refs[eq_name] = refs
    
    # Create a mapping from f_varname to actual equations
    f_name_to_equation = {}
    for eq_name, equation in ode_equations.items():
        # Extract variable name from f_varname
        var_name = eq_name[2:]  # Remove 'f_' prefix
        f_name_to_equation[f"f_{var_name}"] = equation
    
    # Second pass: substitute derivative references
    for eq_name, equation in ode_equations.items():
        resolved_equation = equation
        
        # Replace each f_varname reference with its equation wrapped in parentheses
        for ref in derivative_refs[eq_name]:
            f_ref = f"f_{ref}"
            if f_ref in f_name_to_equation:
                # Wrap the substituted equation in parentheses to maintain precedence
                substitution = f"({f_name_to_equation[f_ref]})"
                resolved_equation = resolved_equation.replace(f_ref, substitution)
            else:
                raise ValueError(f"Reference to undefined derivative: {f_ref} in equation {eq_name}")
        
        resolved_equations[eq_name] = resolved_equation
    
    return resolved_equations


def render_template(template: str, context: dict) -> str:
    """Render a Jinja2 template with the given context."""
    try:
        from jinja2 import Template
    except ImportError:
        raise ImportError("You need to install jinja2: pip install jinja2")
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

    t0 = config["tspan"]["t0"]
    t1 = config["tspan"]["t1"]
    dt = config["solver"]["dt"]
    method = config["solver"].get("method", "Tsit5")

    # Resolve derivative cross-references in ODE equations
    resolved_ode_equations = resolve_derivative_references(ode_equations, variable_names)

    context = {
        "model_name": config["model_name"],
        "parameters": parameters,
        "variable_names": variable_names,
        "initial_conditions": init_vals,
        "ode_equations": resolved_ode_equations,  # Use resolved equations
        "t0": t0,
        "t1": t1,
        "dt": dt,
        "method": method,
        "variable_count": len(variable_names),
    }
    if auxiliary_equations is not None:
        context["auxiliary_equations"] = auxiliary_equations

    # For index consistency:
    equation_ordered = []
    for i, name in enumerate(variable_names):
        eq_name = f"f_{name}"
        if eq_name in resolved_ode_equations:  # Use resolved equations
            equation_ordered.append((eq_name, resolved_ode_equations[eq_name]))
        else:
            raise ValueError(f"Missing ODE for variable: {name}")
    context["ode_equations"] = {k: v for k, v in equation_ordered}

    # Only include struct code for GUI version
    if gui_version:
        context["julia_struct_code"] = generate_julia_struct(model_name, parameters)

    julia_code = render_template(template, context)
    outpath = model_dir / f"{model_name}{suffix}.jl"
    with open(outpath, "w") as f:
        f.write(julia_code)

    print(f"Wrote Julia code to: {outpath}")

    # Debug output to show what transformations were made
    print("\nDerivative reference resolutions:")
    for eq_name in ode_equations:
        if ode_equations[eq_name] != resolved_ode_equations[eq_name]:
            print(f"  {eq_name}:")
            print(f"    Original: {ode_equations[eq_name]}")
            print(f"    Resolved: {resolved_ode_equations[eq_name]}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python3 generate_julia_odesolver.py <model_name>")
        sys.exit(1)

    TEMPLATE_1_PATH = Path(__file__).parent / "templates" / "ode_simsolver.jl.template"
    #TEMPLATE_2_PATH = Path(__file__).parent / "templates" / "ode_simsolver_cmdl.jl.template"
    TEMPLATE_2_PATH = "./templates/ode_simsolver_cmdl.jl.template"
    
    model_name = sys.argv[1]
    # Read and process GUI template
    with open(TEMPLATE_1_PATH, 'r') as f:
        gui_template = f.read()
        generate_julia_code(model_name, gui_template)
    
    # Read and process standalone template
    with open(TEMPLATE_2_PATH, 'r') as f:
        standalone_template = f.read()
        generate_julia_code(model_name, standalone_template, gui_version=False)
        #print(f"Read in template: {standalone_template}")
    
    print(f"Generated GUI and standalone Julia ODE solvers for model: {model_name}")
    print("You can now use a GUI controller, or run standalone:")
    print(f"julia models/{model_name}_cmdl.jl")