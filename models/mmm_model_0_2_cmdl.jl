# -*- coding: utf-8 -*-
# mmm_model_0_2_cmdl.jl - DAE Command-line version

using DifferentialEquations
using Sundials  # For IDA solver

# Parameters

const N0 = 100.0

const A0 = 1.0

const alpha = 0.02

const beta = 0.01

const K0 = 100.0

const nu = 2.5

const tau_P = 0.1

const c_G = 0.3

const i_G = 0.03

const r_T = 0.3

const monopoly = 0.2

const s = 0.2

const Phi_d = 0.05

const Phi_c = 1.0

const gamma_p = 2.0

const varpi = 0.1

const deprec = 0.05

const a_i = 0.05

const b_i = 0.05

const c_i = 1.75

const d_i = 0.0

const gamma_i = 2.0


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
# The IDA solver requires the `differential_vars` argument to specify which
# variables are differential (true) and which are algebraic (false).
# This assumes all variables are differential.
prob = DAEProblem(dae!, du0, u0, tspan, differential_vars = [true, true, true, true])

# Output file
outfile = open("models/mmm_model_0_2.csv", "w")
write(outfile, "t,P,D,u_s,lambda\n")

# Callback for writing results
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

# Solve the DAE
cb = DiscreteCallback((f,t,integrator)->true, step_callback)
sol = solve(prob, IDA(), dt=dt, adaptive=false, callback=cb, abstol=1e-8, reltol=1e-6)

# Cleanup
close(outfile)
println("Simulation completed successfully")