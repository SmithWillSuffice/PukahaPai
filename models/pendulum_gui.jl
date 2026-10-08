# -*- coding: utf-8 -*-
# pendulum_gui.jl - DAE GUI version

using DifferentialEquations
using Sundials
using Mmap
using Sockets
using SharedArrays

using LinearAlgebra, ForwardDiff

function compute_ode_jacobian(integrator)
    u = integrator.u
    du = integrator.du
    p = integrator.p
    t = integrator.t

    # dae! defines F(du,u,t) = du - f(u,t), so the ODE Jacobian is
    # J_ode = df/du = -dF/du when du is held fixed.
    J_residual = ForwardDiff.jacobian(u_var -> begin
        tmp = similar(u_var)
        dae!(tmp, du, u_var, p, t)
        return tmp
    end, u)

    J_ode = -J_residual
    return J_ode
end



function compute_jacobian_and_eigenvals(integrator)
    J_ode = compute_ode_jacobian(integrator)
    return eigvals(J_ode)
end



mutable struct LargestLyapunovState
    v::Vector{Float64}
    log_sum::Float64
    elapsed::Float64
    since_renormalize::Float64
    last_t::Float64
    started::Bool
end

function make_largest_lyapunov_state(n, t_start)
    v = ones(Float64, n)
    v ./= norm(v)
    return LargestLyapunovState(v, 0.0, 0.0, 0.0, Float64(t_start), false)
end

function update_largest_lyapunov!(integrator, state, outfile; transient, renormalize_dt)
    t = Float64(integrator.t)
    analysis_start = t0 + transient

    if !state.started
        if t < analysis_start
            state.last_t = t
            return false
        end
        state.v .= 1.0
        state.v ./= norm(state.v)
        state.log_sum = 0.0
        state.elapsed = 0.0
        state.since_renormalize = 0.0
        state.last_t = t
        state.started = true
        return false
    end

    delta_t = t - state.last_t
    if delta_t <= 0.0
        return false
    end

    J = compute_ode_jacobian(integrator)
    state.v .= exp(J * delta_t) * state.v
    state.elapsed += delta_t
    state.since_renormalize += delta_t
    state.last_t = t

    if state.since_renormalize + eps(Float64) >= renormalize_dt
        stretch = norm(state.v)
        if isfinite(stretch) && stretch > 0.0
            state.log_sum += log(stretch)
            state.v ./= stretch
            lambda_max = state.log_sum / state.elapsed
            write(outfile, "$(t),$(lambda_max)\n")
            flush(outfile)
        end
        state.since_renormalize = 0.0
    end

    return false
end

function finalize_largest_lyapunov!(state, outfile)
    if !state.started || state.elapsed <= 0.0 || state.since_renormalize <= eps(Float64)
        return
    end

    stretch = norm(state.v)
    if isfinite(stretch) && stretch > 0.0
        lambda_max = (state.log_sum + log(stretch)) / state.elapsed
        write(outfile, "$(state.last_t),$(lambda_max)\n")
        flush(outfile)
    end
end


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
    
    theta = u[1]
    
    omega = u[2]
    

    
    dtheta_dt = du[1]
    
    domega_dt = du[2]
    

    

    
    f_theta = omega
    
    f_omega = -damping * omega - (g / length) * sin(theta)
    

    
    out[1] = dtheta_dt - f_theta
    
    out[2] = domega_dt - f_omega
    
end

function main()
    u0 = [
        
        0.785398,
        
        0.0
        
    ]

    du0 = zeros(2)
    tspan = (t0, t1)
    prob = DAEProblem(
        dae!, du0, u0, tspan,
        differential_vars = [true, true]
    )

    outfile = open("models/pendulum.csv", "w")
    write(outfile, "t,theta,omega\n")

    
    eigen_outfile = open("models/pendulum_eigen.csv", "w")
    write(eigen_outfile, "t,e1,e2\n")
    

    
    lyapunov_outfile = open("models/pendulum_lyapunov.csv", "w")
    write(lyapunov_outfile, "t,lambda_max\n")
    lyapunov_state = make_largest_lyapunov_state(2, t0)
    

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

    
    stability_callback = function (integrator)
        if integrator.iter % 50 == 0
            eigs = compute_jacobian_and_eigenvals(integrator)
            max_real = maximum(real.(eigs))
            if max_real > 0
                println("Locally unstable at t=$(integrator.t), max eigenvalue real part: $max_real")
            end
            if isopen(eigen_outfile)
                write(eigen_outfile, string(integrator.t))
                for val in eigs
                    write(eigen_outfile, "," * string(val))
                end
                write(eigen_outfile, "\n")
                flush(eigen_outfile)
            end
        end
        return false
    end
    

    
    lyapunov_callback = function (integrator)
        return update_largest_lyapunov!(
            integrator,
            lyapunov_state,
            lyapunov_outfile;
            transient=20.0,
            renormalize_dt=0.1,
        )
    end
    

    callbacks = Any[
        DiscreteCallback((u,t,integrator)->true, step_callback),
    ]
    
    push!(callbacks, DiscreteCallback((u,t,integrator)->true, stability_callback))
    
    
    push!(callbacks, DiscreteCallback((u,t,integrator)->true, lyapunov_callback))
    
    cb = Base.length(callbacks) == 1 ? callbacks[1] : CallbackSet(callbacks...)

    sol = solve(prob, IDA(), dt=dt, adaptive=false, callback=cb, abstol=1e-8, reltol=1e-6)

    
    finalize_largest_lyapunov!(lyapunov_state, lyapunov_outfile)
    

    close(outfile)
    
    close(eigen_outfile)
    
    
    close(lyapunov_outfile)
    
    println("GUI simulation completed successfully")
end

main()