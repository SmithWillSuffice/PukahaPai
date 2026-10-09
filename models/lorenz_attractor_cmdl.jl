# -*- coding: utf-8 -*-
# lorenz_attractor_cmdl.jl - generated command-line solver

using DifferentialEquations


using LinearAlgebra, ForwardDiff


# Parameters

const sigma = 10.0

const rho = 28.0

const beta = 2.6


# Time/output parameters
const t0 = 0.0
const t1 = 40.0
const dt = 0.01
const output_dt = 0.01

# Explicit right-hand side shared by ODE and DAE modes.
function rhs!(out, u, p, t)
    
    x = u[1]
    
    y = u[2]
    
    z = u[3]
    

    

    
    f_x = sigma * (y - x)
    
    f_y = x * (rho - z) - y
    
    f_z = x * y - beta * z
    

    
    out[1] = f_x
    
    out[2] = f_y
    
    out[3] = f_z
    
    return nothing
end

# Residual wrapper required only by DAE solvers such as IDA.
function dae!(out, du, u, p, t)
    rhs!(out, u, p, t)
    
    out[1] = du[1] - out[1]
    
    out[2] = du[2] - out[2]
    
    out[3] = du[3] - out[3]
    
    return nothing
end


function rhs_vector(u, p, t)
    out = similar(u)
    rhs!(out, u, p, t)
    return out
end

# Differentiate the explicit ODE RHS directly.  This avoids the historical
# residual-Jacobian sign ambiguity even when IDA is selected for integration.
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

# Fourth-order approximation to exp(J*h)*v for a frozen Jacobian J.
# This removes a dense matrix exponential from every solver step while keeping
# the same piecewise-constant-J approximation used by the original diagnostic.
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


# Initial conditions follow [variables].names order.
u0 = [
    
    1.0,
    
    0.0,
    
    0.0
    
]

tspan = (t0, t1)

prob = ODEProblem(rhs!, u0, tspan)



eigen_outfile = open("models/lorenz_attractor_eigen.csv", "w")
write(eigen_outfile, "t,e1,e2,e3\n")



lyapunov_outfile = open("models/lorenz_attractor_lyapunov.csv", "w")
write(lyapunov_outfile, "t,lambda_max\n")
lyapunov_state = make_largest_lyapunov_state(3, t0)


callbacks = Any[]


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
        transient=5.0,
        renormalize_dt=0.1,
    )
end
push!(callbacks, DiscreteCallback((u,t,integrator)->true, lyapunov_callback; save_positions=(false, false)))


cb = Base.isempty(callbacks) ? nothing :
     (Base.length(callbacks) == 1 ? callbacks[1] : CallbackSet(callbacks...))

# Honour the TOML-selected DifferentialEquations.jl algorithm.
if cb === nothing
    sol = solve(
        prob, Tsit5();
        dt=dt,
        adaptive=false,
        saveat=output_dt,
        save_everystep=false,
        abstol=1e-08,
        reltol=1e-06,
    )
else
    sol = solve(
        prob, Tsit5();
        dt=dt,
        adaptive=false,
        saveat=output_dt,
        save_everystep=false,
        callback=cb,
        abstol=1e-08,
        reltol=1e-06,
    )
end


finalize_largest_lyapunov!(lyapunov_state, lyapunov_outfile)


# Command-line runs are not streamed to another process: write the saved
# solution in one buffered pass after integration instead of flushing each row.
open("models/lorenz_attractor.csv", "w") do outfile
    write(outfile, "t,x,y,z\n")
    for i in eachindex(sol.t)
        write(outfile, string(sol.t[i]))
        y = sol.u[i]
        
        write(outfile, "," * string(y[1]))
        
        write(outfile, "," * string(y[2]))
        
        write(outfile, "," * string(y[3]))
        
        write(outfile, "\n")
    end
end


close(eigen_outfile)


close(lyapunov_outfile)


println("Simulation completed successfully using Tsit5() on a ODEProblem")