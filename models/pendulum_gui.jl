# -*- coding: utf-8 -*-
# pendulum_gui.jl - DAE GUI version

using DifferentialEquations
using Sundials
using Mmap
using Sockets
using SharedArrays

# Auto-generated struct for shared memory interop
struct pendulum_Shared
    state::UInt8
    t0::Float64
    t1::Float64

    mass::Float64

    length::Float64

    damping::Float64

    g::Float64

end

function open_shared_pendulum()
    shmpath = "/dev/shm/pukaha_shared"
    sz = sizeof(pendulum_Shared)
    if !isfile(shmpath)
        error("Shared memory file not found - is the GUI controller running?")
    elseif filesize(shmpath) != sz
        error("Shared memory size mismatch - please restart the GUI")
    end
    fd = nothing
    try
        fd = open(shmpath, "r+")
        arr = Mmap.mmap(fd, Vector{UInt8}, sz)
        return arr, Ptr{ pendulum_Shared }(pointer(arr))
    catch e
        fd !== nothing && close(fd)
        rethrow(e)
    end
end

function read_shared_params()
    arr, ptr = open_shared_pendulum()
    try
        return unsafe_load(ptr)
    finally
        finalize(arr)
    end
end

function write_shared_state(new_state::Char)
    arr, ptr = open_shared_pendulum()
    try
        unsafe_store!(Ptr{UInt8}(pointer(arr)), UInt8(new_state))
    finally
        finalize(arr)
    end
end

function check_gui_state()
    arr, ptr = open_shared_pendulum()
    try
        state_byte = unsafe_load(Ptr{UInt8}(pointer(arr)))
        return Char(state_byte)
    finally
        finalize(arr)
    end
end

# Time parameters
const t0 = 0.0
const t1 = 100.0
const dt = 0.01

function dae!(out, du, u, p, t)
    # Extract state variables
    
    theta = u[1]
    
    omega = u[2]
    

    # Extract derivatives
    
    dtheta_dt = du[1]
    
    domega_dt = du[2]
    

    # Auxiliary equations
    

    # Compute f_<var> expressions
    
    f_theta = omega
    
    f_omega = -damping * omega - (g / length) * sin(theta)
    

    
    out[1] = dtheta_dt - f_theta
    
    out[2] = domega_dt - f_omega
    
end

function main()
    # Initial conditions for state variables
    u0 = [
        
        0.785398,
        
        0.0
        
    ]

    # Initial guess for derivatives (can be zeros)
    du0 = zeros(2)

    # Problem setup
    tspan = (t0, t1)
    prob = DAEProblem(dae!, du0, u0, tspan, differential_vars = [true, true])

    # Callback for writing results to a file for GUI visualization
    # In a production GUI, this would write to shared memory.
    outfile = open("models/pendulum.csv", "w")
    write(outfile, "t,theta,omega\n")

    step_callback = function (integrator)
        t = integrator.t
        y = integrator.u
        write(outfile, string(t))
        
        write(outfile, "," * string(y[1]))
        
        write(outfile, "," * string(y[2]))
        
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