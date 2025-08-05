# -*- coding: utf-8 -*-
# pendulum_cmdl.jl - DAE Command-line version

using DifferentialEquations
using Sundials  # For IDA solver



# Parameters

const mass = 1.0

const length = 1.0

const damping = 0.1

const g = 9.81


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

# Initial conditions for state variables
u0 = [
    
    0.785398,
    
    0.0
    
]

# Initial guess for derivatives (can be zeros)
du0 = zeros(2)

# Problem setup
tspan = (t0, t1)
# The IDA solver requires the `differential_vars` argument to specify which
# variables are differential (true) and which are algebraic (false).
# This assumes all variables are differential.
prob = DAEProblem(dae!, du0, u0, tspan, differential_vars = [true, true])

# Output file
outfile = open("models/pendulum.csv", "w")


write(outfile, "t,theta,omega\n")

# Callback for writing results
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

# Solve the DAE
sol = solve(prob, IDA(), dt=dt, adaptive=false, callback=cb, abstol=1e-8, reltol=1e-6)

# Cleanup
close(outfile)

println("Simulation completed successfully")