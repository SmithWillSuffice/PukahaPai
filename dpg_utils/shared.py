#-*- coding: utf-8 -*-
'''
Helper functions for pukahaPai
================================
This module provides shared memory management and GUI integration for the pukahaPai simulation.
'''
import ctypes
from multiprocessing import shared_memory
import os
import toml
import subprocess

# -------- Configuration --------
INIT_PATH = "./init"
MODELS_DIR = "./models"
SHM_NAME = "pukaha_shared"


def load_model_spec(model_path):
    """Enhanced to include tspan parameters"""
    data = toml.load(model_path)
    # Parse regular parameters
    raw_params = data.get("parameters", {})
    parsed = {}
    for name, val in raw_params.items():
        if isinstance(val, float):
            parsed[name] = ("c_double", val)
        elif isinstance(val, int):
            parsed[name] = ("c_int", val)
        else:
            raise ValueError(f"Unsupported param type for '{name}'")
    # Add tspan parameters to shared memory
    tspan = data.get("tspan", {})
    parsed["t0"] = ("c_double", tspan.get("t0", 0.0))
    parsed["t1"] = ("c_double", tspan.get("t1", 10.0))  # This becomes controllable
    
    return parsed


def create_ctypes_struct(param_dict):
    """Enhanced struct creation - order matters for Julia compatibility"""
    fields = [("state", ctypes.c_char)]
    # Add t0, t1 first (to match Julia struct order)
    if "t0" in param_dict:
        fields.append(("t0", ctypes.c_double))
    if "t1" in param_dict:
        fields.append(("t1", ctypes.c_double))
    
    # Add other parameters
    for name, (typ, _) in param_dict.items():
        if name not in ["t0", "t1"]:  # Skip these, already added
            fields.append((name, getattr(ctypes, typ)))
    return type("ParamStruct", (ctypes.Structure,), {"_fields_": fields})


class SharedSimState:
    def __init__(self, param_dict):
        self.ParamStruct = create_ctypes_struct(param_dict)
        self.struct_size = ctypes.sizeof(self.ParamStruct)
        try:
            self.shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=self.struct_size)
            self.is_owner = True
        except FileExistsError:
            self.shm = shared_memory.SharedMemory(name=SHM_NAME, create=False, size=self.struct_size)
            self.is_owner = False
        
        self.buf = self.shm.buf
        self.struct = self.ParamStruct.from_buffer(self.buf)
        self.julia_process = None
        
        if self.is_owner:
            self.struct.state = b'i'
            for name, (_, val) in param_dict.items():
                setattr(self.struct, name, val)

    def get_state(self):
        return self.struct.state.decode()

    def set_state(self, s):
        if isinstance(s, str) and len(s) > 0:
            self.struct.state = s[0].encode()
        else:
            self.struct.state = b'i'

    def get_param(self, name):
        return getattr(self.struct, name)

    def set_param(self, name, value):
        setattr(self.struct, name, value)

    def release(self):
        # Explicitly delete struct and buffer references
        if hasattr(self, "struct"):
            del self.struct
        if hasattr(self, "buf"):
            del self.buf

    def close(self):
        self.shm.close()
        if self.is_owner:
            self.shm.unlink()

    def start_julia_solver(self, model_name):
        """Start Julia solver in separate process"""
        julia_script = f"./models/{model_name}.jl"
        if not os.path.exists(julia_script):
            print(f"Error: Julia solver '{julia_script}' not found.")
            return False
            
        try:
            self.julia_process = subprocess.Popen(
                ["julia", julia_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True  # For easier debugging
            )
            return True
        except Exception as e:
            print(f"Failed to start Julia solver: {e}")
            return False
    
    def stop_julia_solver(self):
        """Stop Julia solver process"""
        if self.julia_process and self.julia_process.poll() is None:
            self.julia_process.terminate()
            self.julia_process.wait()
    
    def is_julia_running(self):
        """Check if Julia process is still running"""
        return self.julia_process and self.julia_process.poll() is None
    