# -*- coding: utf-8 -*-
# mmm_model_0.1_cmdl.jl - Command-line version

using DifferentialEquations

# Parameters

const N0 = 100.0

const K0 = 100.0

const c_u = 0.9

const nu = 2.5

const alpha = 0.02

const beta = 0.01

const id = 0.03

const monopoly = 0.2

const s = 0.2

const Phi_d = 0.05

const Phi_c = 1.0

const gamma_p = 2.0

const deprec = 0.05

const ai = 0.05

const bi = 0.05

const ci = 1.75

const di = 0.0

const gamma_i = 2.0


# Time parameters
const t0 = 0.0
const t1 = 50.0
const dt = 0.1


# This version does not need shared memory parameters, since
# it is for the cmdl version.

function ode!(du, u, p, t)
    
            P = u[1]
    
            D = u[2]
    
            u = u[3]
    
            lambda = u[4]
    
        # Auxiliary equations
    
    
        A = A0 * exp(alpha * t)
    
        N = N0 * exp(beta * t)
    
        Yr = lambda * A * N
    
        Y = Y * P
    
        K = nu * Y
    
        Phi = Phi_d/(1 - lambda)^gamma_p - Phi_c
    
        Gamma = (1 - u)/nu - deprec
    
        Pi = Y - u*A*L - ib * D
    
        pi = Pi/K
    
        Inv = ai / (bi + ci * pi)^gamma_i - di
    
    
        # ODEs
    
        du[1] = tau_P * (u/(1 - monopoly) - P)
    
        du[2] = Inv - Pi
    
        du[3] = u * (Phi - c_u)
    
        du[4] = lambda * ( Gamma - alpha - beta )
    
end

# Initial conditions
u0 = [

    1.0,

    50.0,

    0.6,

    0.9

]

# Problem setup
tspan = (t0, t1)
prob = ODEProblem(ode!, u0, tspan)

# Output file
outfile = open("models/mmm_model_0.1.csv", "w")
write(outfile, "t,P,D,u,lambda\n")

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

# Solve the ODE
cb = DiscreteCallback((u,t,integrator)->true, step_callback)
sol = solve(prob, Tsit5(), dt=dt, adaptive=false, callback=cb)

# Cleanup
close(outfile)
println("Simulation completed successfully")