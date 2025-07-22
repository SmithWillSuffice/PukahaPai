# -*- coding: utf-8 -*-
'''
Helper functiosn for pukahaPai
==============================
This modules mostly has plotting helper functions.
'''
import os
import toml
import dearpygui.dearpygui as dpg

BUFF = 25

def extract_variable_names(model_path):
    """Extract ODE variable names from [variables] and initial values from [initial_conditions]."""
    data = toml.load(model_path)
    var_section = data.get("variables", {})
    ic_section = data.get("initial_conditions", {})
    y_names = var_section.get("names", [])
    y0 = [ic_section.get(name, 0.0) for name in y_names]
    print(f"Extracted variable names: {y_names} with initial values: {y0}")
    return y_names, y0


#------------ Plot Methods --------------

def add_single_variable_plot(parent, y_name, t_data=None, y_data=None):
    """Add a plot for a single ODE variable."""
    # get parent width and height
    parent_width = dpg.get_item_width(parent)
    with dpg.plot(label=f"{y_name} vs Time", height=180, width=parent_width - BUFF, parent=parent):
        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Time")
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=y_name)
        # Add a line series for this variable
        if t_data is not None and y_data is not None:
            dpg.add_line_series(t_data, y_data, label=y_name, parent=y_axis)
        else:
            dpg.add_line_series([], [], label=y_name, parent=y_axis)



def update_plots(model_name, y_names):
    """Read CSV and update all plots"""
    try:
        csv_path = f"models/{model_name}.csv"
        if not os.path.exists(csv_path):
            return
        data = []
        # Read CSV safely
        with open(csv_path, 'r') as f:
            lines = f.readlines()
            if len(lines) < 2:  # Need at least header + 1 data point
                return
            
            # Parse data
            data = [line.strip().split(',') for line in lines[1:]]  # Skip header
            t = [float(row[0]) for row in data]
            
            # Update each variable's plot
            # for i, y_name in enumerate(y_names, start=1):
            #     y_values = [float(row[i]) for row in data]
            #     dpg.set_value(f"plot_{y_name}", [t, y_values]) 
    
        for y_name in y_names:
            y_values = [float(row[i]) for row in data]
            dpg.set_value(plot_tags[y_name], [t, y_values])  
    except Exception as e:
        print(f"Plot update error: {e}")
