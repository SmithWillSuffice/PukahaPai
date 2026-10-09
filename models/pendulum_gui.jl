# -*- coding: utf-8 -*-
# pendulum_gui.jl - generated GUI solver

using DifferentialEquations
using Mmap
using Sockets
using SharedArrays
using LinearAlgebra, ForwardDiff

function rhs_vector(u, p, t)
    out = similar(u)
    rhs!(out, u, p, t)
    return out
end

function compute_ode_jacobian(integrator)
    u = integrator.u
    p = integrator.p
    t = integrator.t
    return ForwardDiff.jacobian(u_var -> rhs_vector(u_var, p, t), u)
end

function compute_jacobian_and_eigenvals(integrator)
    return eigvals(compute_ode_jacobian(integrator))
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

function propagate_tangent_rk4!(v, J, h)
    k1 = J * v
    k2 = J * (v .+ (0.5 * h) .* k1)
    k3 = J * (v .+ (0.5 * h) .* k2)
    k4 = J * (v .+ h .* k3)
    v .+= (h / 6.0) .* (k1 .+ 2.0 .* k2 .+ 2.0 .* k3 .+ k4)
    return nothing
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
    propagate_tangent_rk4!(state.v, J, delta_t)
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
    end
end

# Auto-generated struct for shared memory interop.
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

# Parameter snapshot used by rhs!.  It is refreshed from shared memory by the
# GUI output callback rather than mmap-reading on every RHS evaluation.
const GUI_PARAMS = Ref{Union{Nothing, pendulum_Shared}}(nothing)

const t0 = 0.0
const t1 = 100.0
const dt = 0.01
const output_dt = 0.01
const output_flush_every = 10

function rhs!(out, u, p, t)
    shared = GUI_PARAMS[]
    shared === nothing && error("GUI parameters have not been initialized")
    mass = shared.mass
    length = shared.length
    damping = shared.damping
    g = shared.g
    theta = u[1]
    omega = u[2]
    f_theta = omega
    f_omega = -damping * omega - (g / length) * sin(theta)
    out[1] = f_theta
    out[2] = f_omega
    return nothing
end

function dae!(out, du, u, p, t)
    rhs!(out, u, p, t)
    out[1] = du[1] - out[1]
    out[2] = du[2] - out[2]
    return nothing
end

function main()
    GUI_PARAMS[] = read_shared_params()

    u0 = [
        0.785398,
        0.0
    ]

    tspan = (t0, t1)
    prob = ODEProblem(rhs!, u0, tspan)

    outfile = open("models/pendulum.csv", "w")
    write(outfile, "t,theta,omega\n")

    eigen_outfile = open("models/pendulum_eigen.csv", "w")
    write(eigen_outfile, "t,e1,e2\n")

    lyapunov_outfile = open("models/pendulum_lyapunov.csv", "w")
    write(lyapunov_outfile, "t,lambda_max\n")
    lyapunov_state = make_largest_lyapunov_state(2, t0)

    # GUI output is streamed, so flush periodically rather than once per row.
    next_output_t = Ref(t0)
    output_rows_since_flush = Ref(0)
    step_callback = function (integrator)
        # Refresh GUI-controlled parameters at the output cadence, not at every
        # internal RHS evaluation.
        GUI_PARAMS[] = read_shared_params()
        t = Float64(integrator.t)
        if t + eps(Float64) < next_output_t[]
            return false
        end

        y = integrator.u
        write(outfile, string(t))
        write(outfile, "," * string(y[1]))
        write(outfile, "," * string(y[2]))
        write(outfile, "\n")

        output_rows_since_flush[] += 1
        if output_rows_since_flush[] >= output_flush_every
            flush(outfile)
            output_rows_since_flush[] = 0
        end

        while next_output_t[] <= t + eps(Float64)
            next_output_t[] += output_dt
        end
        return false
    end

    callbacks = Any[
        DiscreteCallback((u,t,integrator)->true, step_callback; save_positions=(false, false)),
    ]

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
            end
        end
        return false
    end
    push!(callbacks, DiscreteCallback((u,t,integrator)->true, stability_callback; save_positions=(false, false)))

    lyapunov_callback = function (integrator)
        return update_largest_lyapunov!(
            integrator,
            lyapunov_state,
            lyapunov_outfile;
            transient=20.0,
            renormalize_dt=0.1,
        )
    end
    push!(callbacks, DiscreteCallback((u,t,integrator)->true, lyapunov_callback; save_positions=(false, false)))

    cb = Base.length(callbacks) == 1 ? callbacks[1] : CallbackSet(callbacks...)

    sol = solve(
        prob, Tsit5();
        dt=dt,
        adaptive=false,
        save_everystep=false,
        callback=cb,
        abstol=1e-08,
        reltol=1e-06,
    )

    finalize_largest_lyapunov!(lyapunov_state, lyapunov_outfile)

    flush(outfile)
    close(outfile)
    close(eigen_outfile)
    close(lyapunov_outfile)
    println("GUI simulation completed successfully using Tsit5() on a ODEProblem")
end

main()
