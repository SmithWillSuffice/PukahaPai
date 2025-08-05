# -*- coding: utf-8 -*-
# lorenz_attractor_cmdl.jl - DAE Command-line version

using DifferentialEquations
using Sundials  # For IDA solver



# Parameters

const sigma = 10.0

const rho = 28.0

const beta = 2.6


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
# The IDA solver requires the `differential_vars` argument to specify which
# variables are differential (true) and which are algebraic (false).
# This assumes all variables are differential.
prob = DAEProblem(dae!, du0, u0, tspan, differential_vars = [true, true, true])

# Output file
outfile = open("models/lorenz_attractor.csv", "w")


write(outfile, "t,x,y,z\n")

# Callback for writing results
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

# Solve the DAE
sol = solve(prob, IDA(), dt=dt, adaptive=false, callback=cb, abstol=1e-8, reltol=1e-6)

# Cleanup
close(outfile)

println("Simulation completed successfully")