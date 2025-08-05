# -*- coding: utf-8 -*-
# lorenz_attractor_gui.jl - DAE GUI version

using DifferentialEquations
using Sundials
using Mmap
using Sockets
using SharedArrays

# Functions for getting eigenvalues (optional)


# Auto-generated struct for shared memory interop
struct lorenz_attractor_Shared
    state::UInt8
    t0::Float64
    t1::Float64

    sigma::Float64

    rho::Float64

    beta::Float64

end

function open_shared_lorenz_attractor()
    shmpath = "/dev/shm/pukaha_shared"
    sz = sizeof(lorenz_attractor_Shared)
    if !isfile(shmpath)
        error("Shared memory file not found - is the GUI controller running?")
    elseif filesize(shmpath) != sz
        error("Shared memory size mismatch - please restart the GUI")
    end
    fd = nothing
    try
        fd = open(shmpath, "r+")
        arr = Mmap.mmap(fd, Vector{UInt8}, sz)
        return arr, Ptr{ lorenz_attractor_Shared }(pointer(arr))
    catch e
        fd !== nothing && close(fd)
        rethrow(e)
    end
end

function read_shared_params()
    arr, ptr = open_shared_lorenz_attractor()
    try
        return unsafe_load(ptr)
    finally
        finalize(arr)
    end
end

function write_shared_state(new_state::Char)
    arr, ptr = open_shared_lorenz_attractor()
    try
        unsafe_store!(Ptr{UInt8}(pointer(arr)), UInt8(new_state))
    finally
        finalize(arr)
    end
end

function check_gui_state()
    arr, ptr = open_shared_lorenz_attractor()
    try
        state_byte = unsafe_load(Ptr{UInt8}(pointer(arr)))
        return Char(state_byte)
    finally
        finalize(arr)
    end
end

# Time parameters
const t0 = 0.0
const t1 = 40.0
const dt = 0.01

function dae!(out, du, u, p, t)
    # Extract state variables
    
    x = u[1]
    
    y = u[2]
    
    z = u[3]
    

    # Extract derivatives
    
    dx_dt = du[1]
    
    dy_dt = du[2]
    
    dz_dt = du[3]
    

    # Auxiliary equations
    

    # Compute f_<var> expressions
    
    f_x = sigma * (y - x)
    
    f_y = x * (rho - z) - y
    
    f_z = x * y - beta * z
    

    
    out[1] = dx_dt - f_x
    
    out[2] = dy_dt - f_y
    
    out[3] = dz_dt - f_z
    
end

function main()
    # Initial conditions for state variables
    u0 = [
        
        1.0,
        
        0.0,
        
        0.0
        
    ]

    # Initial guess for derivatives (can be zeros)
    du0 = zeros(3)

    # Problem setup
    tspan = (t0, t1)
    prob = DAEProblem(dae!, du0, u0, tspan, differential_vars = [true, true, true])

    # Callback for writing results to a file for GUI visualization
    # In a production GUI, this would write to shared memory.
    outfile = open("models/lorenz_attractor.csv", "w")
    
    write(outfile, "t,x,y,z\n")

    step_callback = function (integrator)
        t = integrator.t
        y = integrator.u
        write(outfile, string(t))
        
        write(outfile, "," * string(y[1]))
        
        write(outfile, "," * string(y[2]))
        
        write(outfile, "," * string(y[3]))
        
        write(outfile, "\n")
        flush(outfile)
        return false
    end
    
    cb = DiscreteCallback((f,t,integrator)->true, step_callback)
    
    sol = solve(prob, IDA(), dt=dt, adaptive=false, callback=cb, abstol=1e-8, reltol=1e-6)

    close(outfile)
    
    println("GUI simulation completed successfully")
end

# Execute main function
main()