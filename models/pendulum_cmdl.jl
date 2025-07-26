# -*- coding: utf-8 -*-
# pendulum_cmdl.jl - Command-line version

using DifferentialEquations

# Parameters

const mass = 1.0

const length = 1.0

const damping = 0.1

const g = 9.81


# Time parameters
const t0 = 0.0
const t1 = 100.0
const dt = 0.01


# This version does not need shared memory parameters, since
# it is for the cmdl version.

function ode!(du, u, p, t)
    
            theta = u[1]
    
            omega = u[2]
    
        # Auxiliary equations
    
        # ODEs
    
        du[1] = omega
    
        du[2] = -damping * omega - (g / length) * sin(theta)
    
end

# Initial conditions
u0 = [

    0.785398,

    0.0

]

# Problem setup
tspan = (t0, t1)
prob = ODEProblem(ode!, u0, tspan)

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

# Solve the ODE
cb = DiscreteCallback((u,t,integrator)->true, step_callback)
sol = solve(prob, Tsit5(), dt=dt, adaptive=false, callback=cb)

# Cleanup
close(outfile)
println("Simulation completed successfully")