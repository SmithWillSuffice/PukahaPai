# -*- coding: utf-8 -*-
# mmm_model_0_2_gui.jl - DAE GUI version

using DifferentialEquations
using Sundials
using Mmap
using Sockets
using SharedArrays

# Auto-generated struct for shared memory interop
struct mmm_model_0_2_Shared
    state::UInt8
    t0::Float64
    t1::Float64

    N0::Float64

    A0::Float64

    alpha::Float64

    beta::Float64

    K0::Float64

    nu::Float64

    tau_P::Float64

    c_G::Float64

    i_G::Float64

    r_T::Float64

    monopoly::Float64

    s::Float64

    Phi_d::Float64

    Phi_c::Float64

    gamma_p::Float64

    varpi::Float64

    deprec::Float64

    a_i::Float64

    b_i::Float64

    c_i::Float64

    d_i::Float64

    gamma_i::Float64

end

function open_shared_mmm_model_0_2()
    shmpath = "/dev/shm/pukaha_shared"
    sz = sizeof(mmm_model_0_2_Shared)
    if !isfile(shmpath)
        error("Shared memory file not found - is the GUI controller running?")
    elseif filesize(shmpath) != sz
        error("Shared memory size mismatch - please restart the GUI")
    end
    fd = nothing
    try
        fd = open(shmpath, "r+")
        arr = Mmap.mmap(fd, Vector{UInt8}, sz)
        return arr, Ptr{ mmm_model_0_2_Shared }(pointer(arr))
    catch e
        fd !== nothing && close(fd)
        rethrow(e)
    end
end

function read_shared_params()
    arr, ptr = open_shared_mmm_model_0_2()
    try
        return unsafe_load(ptr)
    finally
        finalize(arr)
    end
end

function write_shared_state(new_state::Char)
    arr, ptr = open_shared_mmm_model_0_2()
    try
        unsafe_store!(Ptr{UInt8}(pointer(arr)), UInt8(new_state))
    finally
        finalize(arr)
    end
end

function check_gui_state()
    arr, ptr = open_shared_mmm_model_0_2()
    try
        state_byte = unsafe_load(Ptr{UInt8}(pointer(arr)))
        return Char(state_byte)
    finally
        finalize(arr)
    end
end

# Time parameters
const t0 = 0.0
const t1 = 50.0
const dt = 0.1

function dae!(out, du, u, p, t)
    # Extract state variables
    
    P = u[1]
    
    D = u[2]
    
    u_s = u[3]
    
    lambda = u[4]
    

    # Extract derivatives
    
    dP_dt = du[1]
    
    dD_dt = du[2]
    
    du_s_dt = du[3]
    
    dlambda_dt = du[4]
    

    # Auxiliary equations
    
    A = A0 * exp(alpha * t)
    
    N = N0 * exp(beta * t)
    
    Yr = lambda * A * N
    
    Y = Yr * P
    
    L = lambda * N
    
    K = nu * Y
    
    G = c_G * Y
    
    T = r_T * Y
    
    Phi = Phi_d/(1 - lambda)^gamma_p - Phi_c
    
    Gamma = (1 - u_s)/nu - deprec
    
    Pi = Y - u_s*A*L + i_G * D
    
    pi = Pi/K
    
    Inv = a_i / (b_i + c_i * pi)^gamma_i - d_i
    
    S = G - T + Inv * Y
    

    # Compute f_<var> expressions
    
    f_P = tau_P * (u_s/(1 - monopoly) - P)
    
    f_D = G - T
    
    f_lambda = lambda * ( Gamma - deprec - alpha - beta )
    
    f_u_s = u_s * (Phi + varpi * f_lambda / lambda  + f_P / P - alpha)
    

    
    out[1] = dP_dt - f_P
    
    out[2] = dD_dt - f_D
    
    out[3] = du_s_dt - f_u_s
    
    out[4] = dlambda_dt - f_lambda
    
end

function main()
    # Initial conditions for state variables
    u0 = [
        
        1.0,
        
        50.0,
        
        0.6,
        
        0.9
        
    ]

    # Initial guess for derivatives (can be zeros)
    du0 = zeros(4)

    # Problem setup
    tspan = (t0, t1)
    prob = DAEProblem(dae!, du0, u0, tspan, differential_vars = [true, true, true, true])

    # Callback for writing results to a file for GUI visualization
    # In a production GUI, this would write to shared memory.
    outfile = open("models/mmm_model_0_2.csv", "w")
    write(outfile, "t,P,D,u_s,lambda\n")

    step_callback = function (integrator)
        t = integrator.t
        y = integrator.u
        write(outfile, string(t))
        
        write(outfile, "," * string(y[1]))
        
        write(outfile, "," * string(y[2]))
        
        write(outfile, "," * string(y[3]))
        
        write(outfile, "," * string(y[4]))
        
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