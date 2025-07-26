# -*- coding: utf-8 -*-
# lorenz_attractor_cmdl.jl - Command-line version

using DifferentialEquations

# Parameters

const sigma = 10.0

const rho = 28.0

const beta = 2.6


# Time parameters
const t0 = 0.0
const t1 = 40.0
const dt = 0.01


# This version does not need shared memory parameters, since
# it is for the cmdl version.

function ode!(du, u, p, t)
    
            x = u[1]
    
            y = u[2]
    
            z = u[3]
    
        # Auxiliary equations
    
        # ODEs
    
        du[1] = sigma * (y - x)
    
        du[2] = x * (rho - z) - y
    
        du[3] = x * y - beta * z
    
end

# Initial conditions
u0 = [

    1.0,

    0.0,

    0.0

]

# Problem setup
tspan = (t0, t1)
prob = ODEProblem(ode!, u0, tspan)

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

# Solve the ODE
cb = DiscreteCallback((u,t,integrator)->true, step_callback)
sol = solve(prob, Tsit5(), dt=dt, adaptive=false, callback=cb)

# Cleanup
close(outfile)
println("Simulation completed successfully")