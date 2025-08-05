# -*- coding: utf-8 -*-
'''
plot_utils
==========

PukahaPai ODE model plotting tools. For use in ./plots4models.py

| Copyright: (c) 2025 Bijou M. Smith
| License: GNU General Public License v3.0 <https://www.gnu.org/licenses/gpl-
'''

import os
import toml
import numpy as np
import plotly.graph_objects as go
import re


def load_config(model_name):
    config_path = os.path.join("models", f"{model_name}.toml")
    if not os.path.exists(config_path):
        return {}
    return toml.load(config_path)


def convert_julia_to_python(expression, parameters):
    """
    Convert Julia mathematical expressions to Python/NumPy equivalents.
    
    Args:
        expression: Julia expression string
        parameters: Dictionary of parameter values for substitution
    
    Returns:
        Python expression string ready for evaluation
    """
    # Start with the original expression
    py_expr = expression
    
    # Replace Julia exponentiation with Python
    py_expr = re.sub(r'\^', '**', py_expr)
    
    # Replace Julia exp function with numpy exp
    py_expr = re.sub(r'\bexp\(', 'np.exp(', py_expr)
    
    # Replace other common Julia math functions with numpy equivalents
    julia_to_numpy = {
        r'\bsin\(': 'np.sin(',
        r'\bcos\(': 'np.cos(',
        r'\btan\(': 'np.tan(',
        r'\blog\(': 'np.log(',
        r'\bsqrt\(': 'np.sqrt(',
        r'\babs\(': 'np.abs(',
    }
    
    for julia_func, numpy_func in julia_to_numpy.items():
        py_expr = re.sub(julia_func, numpy_func, py_expr)
    
    # Substitute parameter values
    for param_name, param_value in parameters.items():
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(param_name) + r'\b'
        py_expr = re.sub(pattern, str(param_value), py_expr)
    
    return py_expr


def compute_derived_variables(df, config):
    """
    Compute derived variables from auxiliary equations in the config.
    
    Args:
        df: DataFrame with base variables (t and ODE variables)
        config: TOML configuration dictionary
    
    Returns:
        DataFrame with added derived variables
    """
    # Get parameters for substitution
    parameters = config.get("parameters", {})
    
    # Get auxiliary equations
    auxiliary_eqs = config.get("equations", {}).get("auxiliary", {})
    
    if not auxiliary_eqs:
        return df
    
    # Create a copy of the dataframe to avoid modifying the original
    df_extended = df.copy()
    
    # Create a namespace for evaluation that includes numpy and existing columns
    # Handle 'lambda' as a special case since it's a Python keyword
    eval_namespace = {
        'np': np,
        't': df_extended['t'].values,
    }
    
    # Add all existing columns to namespace, handling 'lambda' specially
    for col in df_extended.columns:
        if col == 'lambda':
            eval_namespace['lambda_var'] = df_extended[col].values
        else:
            eval_namespace[col] = df_extended[col].values
    
    # Sort auxiliary equations by dependency (simple topological sort)
    # This ensures variables are computed in the right order
    computed_vars = set(df_extended.columns)
    remaining_eqs = auxiliary_eqs.copy()
    
    max_iterations = len(remaining_eqs) * 2  # Prevent infinite loops
    iteration = 0
    
    while remaining_eqs and iteration < max_iterations:
        iteration += 1
        progress_made = False
        
        for var_name, expression in list(remaining_eqs.items()):
            # Convert Julia expression to Python
            py_expr = convert_julia_to_python(expression, parameters)
            
            # Handle 'lambda' keyword issue by replacing with 'lambda_var'
            py_expr = re.sub(r'\blambda\b', 'lambda_var', py_expr)
            
            # Extract variable names from the expression
            var_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
            expr_vars = set(re.findall(var_pattern, py_expr))
            
            # Remove numpy functions and constants, but keep variable names
            numpy_items = {'np', 'exp', 'sin', 'cos', 'tan', 'log', 'sqrt', 'abs', 'e'}
            # Don't remove 'pi' since it might be a user variable, not np.pi
            expr_vars = expr_vars - numpy_items
            
            # Convert 'lambda' references back for dependency checking
            expr_vars_original = set()
            for var in expr_vars:
                if var == 'lambda_var':
                    expr_vars_original.add('lambda')
                else:
                    expr_vars_original.add(var)
            
            # Check if all required variables are available
            if expr_vars_original.issubset(computed_vars):
                try:
                    # Evaluate the expression
                    result = eval(py_expr, {"__builtins__": {}}, eval_namespace)
                    
                    # Add to dataframe and evaluation namespace
                    df_extended[var_name] = result
                    
                    # Handle special case for lambda in namespace
                    if var_name == 'lambda':
                        eval_namespace['lambda_var'] = result
                    else:
                        eval_namespace[var_name] = result
                    
                    computed_vars.add(var_name)
                    
                    # Remove from remaining equations
                    del remaining_eqs[var_name]
                    progress_made = True
                    
                    print(f"Computed derived variable: {var_name}")
                    
                except Exception as e:
                    print(f"Warning: Could not compute {var_name} = {py_expr}: {e}")
                    # Don't remove immediately, might work in next iteration
            else:
                missing_vars = expr_vars_original - computed_vars
                if iteration == 1:  # Only print on first iteration to avoid spam
                    print(f"Waiting for dependencies for {var_name}: {missing_vars}")
        
        if not progress_made:
            # Try one more time with more detailed error reporting
            print("No progress made, checking remaining equations...")
            for var_name, expression in remaining_eqs.items():
                py_expr = convert_julia_to_python(expression, parameters)
                py_expr = re.sub(r'\blambda\b', 'lambda_var', py_expr)
                
                var_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
                expr_vars = set(re.findall(var_pattern, py_expr))
                numpy_items = {'np', 'exp', 'sin', 'cos', 'tan', 'log', 'sqrt', 'abs', 'e'}
                expr_vars = expr_vars - numpy_items
                
                expr_vars_original = set()
                for var in expr_vars:
                    if var == 'lambda_var':
                        expr_vars_original.add('lambda')
                    else:
                        expr_vars_original.add(var)
                
                missing_vars = expr_vars_original - computed_vars
                available_in_namespace = [var for var in expr_vars if var in eval_namespace]
                
                print(f"  {var_name}: expression = {py_expr}")
                print(f"    required vars: {expr_vars_original}")
                print(f"    missing vars: {missing_vars}")
                print(f"    available in namespace: {available_in_namespace}")
            break
    
    # Warn about any remaining uncomputed variables
    if remaining_eqs:
        print(f"Warning: Could not compute the following derived variables: {list(remaining_eqs.keys())}")
    
    return df_extended


def plot_phase_2d(df, xvar, yvar, aspect=(1.0, 1.0)):
    x = df[xvar]
    y = df[yvar]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name=f"{yvar} vs {xvar}"))

    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()

    fig.update_layout(
        title=f"Phase Plot: {yvar} vs {xvar}",
        xaxis=dict(title=xvar,
            range=[x_min, x_max], 
            showgrid=True,
            gridcolor='rgba(100, 100, 100, 0.3)',  
            zeroline=True,
            zerolinecolor='rgba(100, 100, 100, 0.5)',
            zerolinewidth=1
            ),
        yaxis=dict(title=yvar,
            range=[y_min, y_max],
            showgrid=True,
            gridcolor='rgba(100, 100, 100, 0.3)',
            zeroline=True,
            zerolinecolor='rgba(100, 100, 100, 0.5)',
            zerolinewidth=1,
            ),
        width=int(400 * aspect[0]),
        height=int(400 * aspect[1]),
        paper_bgcolor="black",
        plot_bgcolor="black",
        font=dict(color="white"),
    )
    return fig


def plot_phase_3d(df, xvar, yvar, zvar, aspect=(1.0, 1.0, 1.0)):
    x = df[xvar]
    y = df[yvar]
    z = df[zvar]

    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z,
        mode='lines',
        line=dict(width=2),
        name=f"{zvar} vs {xvar},{yvar}"
    ))

    transparent = 'rgba(0,0,0,0)'

    fig.update_layout(
        title=f"3D Phase Plot: {zvar} vs {xvar},{yvar}",
        scene=dict(
            xaxis_title=xvar,
            yaxis_title=yvar,
            zaxis_title=zvar,
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(100, 100, 100, 0.3)',
                range=[x.min(), x.max()],
                zeroline=True,
                zerolinecolor='rgba(100, 100, 100, 0.5)',
                zerolinewidth=1,
                backgroundcolor=transparent
            ),
            yaxis=dict(
                range=[y.min(), y.max()],
                showgrid=True,
                gridcolor='rgba(100, 100, 100, 0.3)',
                zeroline=True,
                zerolinecolor='rgba(100, 100, 100, 0.5)',
                zerolinewidth=1,
                backgroundcolor=transparent
            ),
            zaxis=dict(
                range=[z.min(), z.max()],
                showgrid=True,
                gridcolor='rgba(100, 100, 100, 0.3)',
                zeroline=True,
                zerolinecolor='rgba(100, 100, 100, 0.5)',
                zerolinewidth=1,
                backgroundcolor=transparent
            ),
            aspectmode="manual",
            aspectratio=dict(
                x=aspect[0],
                y=aspect[1],
                z=aspect[2]
            ),
            bgcolor="black"
        ),
        paper_bgcolor="black",
        plot_bgcolor="black",
        font=dict(color="white"),
        width=500,
        height=500,
    )
    return fig


def plot_time_series(df, time_var, value_vars):
   if len(value_vars) == 1:
      return [plot_single_time_series(df, time_var, value_vars[0])]
   elif len(value_vars) == 2:
      return [plot_dual_axis_time_series(df, time_var, value_vars)]
   else:
      return [plot_single_time_series(df, time_var, var) for var in value_vars]



def plot_single_time_series(df, time_var, value_var):
   fig = go.Figure()
   fig.add_trace(go.Scatter(x=df[time_var], y=df[value_var],
                            mode='lines', name=value_var))
   fig.update_layout(
      title=f"Time Series: {value_var}",
        xaxis=dict( title=time_var,
        showgrid=True,
        gridcolor='rgba(100, 100, 100, 0.3)',
        zeroline=True,
        zerolinecolor='rgba(100, 100, 100, 0.5)',
        zerolinewidth=1
        ),
      yaxis=dict( title=value_var,  
        showgrid=True,
        gridcolor='rgba(100, 100, 100, 0.3)',
        zeroline=True,
        zerolinecolor='rgba(100, 100, 100, 0.5)',
        zerolinewidth=1
        ),
      paper_bgcolor="black",
      plot_bgcolor="black",
      font=dict(color="white"),
      height=400,
   )
   return fig


def plot_dual_axis_time_series(df, time_var, value_vars):
    var1, var2 = value_vars

    # Define line colors (you can change or parameterize these if needed)
    color1 = 'rgb(31, 119, 180)'  # blue
    color2 = 'rgb(255, 127, 14)'  # orange

    # Faint versions for grid/zero lines
    faint1 = 'rgba(31, 119, 180, 0.4)'
    faint2 = 'rgba(255, 127, 14, 0.4)'

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[time_var], y=df[var1],
                                mode='lines', name=var1, yaxis='y1',
                                line=dict(color=color1)))
    fig.add_trace(go.Scatter(x=df[time_var], y=df[var2],
                                mode='lines', name=var2, yaxis='y2',
                                line=dict(color=color2)))

    fig.update_layout(
        title=f"Time Series: {var1} & {var2}",
        paper_bgcolor="black",
        plot_bgcolor="black",
        font=dict(color="white"),
        height=400,
        xaxis=dict(
            title=time_var,
            gridcolor='rgba(100,100,100,0.3)',
            # zeroline=True,
            # zerolinecolor='rgba(150, 150, 150, 0.4)',
            # zerolinewidth=1
        ),
        yaxis=dict(
            title=var1,
            color=color1,
            gridcolor='rgba(100,100,100,0.3)',
            zeroline=True,
            zerolinecolor=faint1,
            zerolinewidth=1,
            titlefont=dict(color=color1),
            tickfont=dict(color=color1)
        ),
        yaxis2=dict(
            title=var2,
            color=color2,
            overlaying='y',
            side='right',
            gridcolor='rgba(100,100,100,0.3)',
            zeroline=True,
            zerolinecolor=faint2,
            zerolinewidth=1,
            titlefont=dict(color=color2),
            tickfont=dict(color=color2)
        )
    )
    return fig

