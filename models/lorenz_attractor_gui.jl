# -*- coding: utf-8 -*-
# lorenz_attractor.jl  - for GUI slaving

using DifferentialEquations
import Base.Libc
using Mmap


# Auto-generated struct for shared memory interop
struct lorenz_attractor_Shared
    state::UInt8
    t0::Float64
    t1::Float64
    sigma::Float64
    rho::Float64
    beta::Float64
end

function open_shared_lorenz_attractor()
    shmpath = "/dev/shm/pukaha_shared"
    sz = sizeof(lorenz_attractor_Shared)
    fd = open(shmpath, "r+")
    arr = Mmap.mmap(Array{UInt8}, fd, sz)
    return arr, Ptr{lorenz_attractor_Shared}(pointer(arr))
end

function read_shared_params()
    """Read current parameters from shared memory"""
    arr, ptr = open_shared_lorenz_attractor()
    return unsafe_load(ptr)
end

function write_shared_state(new_state::Char)
    """Write state back to shared memory"""
    arr, ptr = open_shared_lorenz_attractor()
    shared_data = unsafe_load(ptr)
    unsafe_store!(Ptr{UInt8}(pointer(arr)), UInt8(new_state))
end

function check_gui_state()
    """Check if GUI sent stop/pause signal"""
    arr, ptr = open_shared_lorenz_attractor()
    state_byte = unsafe_load(Ptr{UInt8}(pointer(arr)))
    return Char(state_byte)
end


function solve_ode()
    # Read parameters from shared memory
    params = read_shared_params()
    
    function ode!(du, u, p, t)

        x = u[1]

        y = u[2]

        z = u[3]


        # Extract parameters from shared memory struct

        sigma = params.sigma

        rho = params.rho

        beta = params.beta



        du[1] = sigma * (y - x)

        du[2] = x * (rho - z) - y

        du[3] = x * y - beta * z

    end

    u0 = [

        1.0,

        0.0,

        0.0

    ]

    tspan = (params.t0, params.t1)
    dt = 0.01
    prob = ODEProblem(ode!, u0, tspan)

    outfile = open("models/lorenz_attractor.csv", "w")
    write(outfile, "t,x,y,z\n")

    step_callback = function (integrator)
        # Check for GUI state changes
        state = check_gui_state()
        
        if state == 'q'  # Quit signal
            close(outfile)
            terminate!(integrator)
            return true
        elseif state == 'p'  # Pause signal
            # For now, just continue (could implement pause logic later)
            return false
        end
        
        # Write data to file
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

    # DON'T set state to 'r' here - let GUI control it
    
    cb = DiscreteCallback((u,t,integrator)->true, step_callback)
    
    try
        sol = solve(prob, Tsit5(), dt=dt, adaptive=false, callback=cb)
        println("Simulation completed successfully")
    catch e
        println("Solver error: ", e)
        write_shared_state('e')  # Error state
    finally
        close(outfile)
    end
end

# Main execution loop
function main()
    println("Julia solver started for lorenz_attractor")
    
    # Check if shared memory file exists
    if !isfile("/dev/shm/pukaha_shared")
        error("Shared memory file not found - is the GUI controller running?")
    end
    
    try
        # Continuous loop - don't exit after one simulation
        while true
            state = check_gui_state()
            
            if state == 'r'
                println("Starting simulation...")
                solve_ode()
                # Don't break here! Continue looping to allow restarts
                write_shared_state('i')  # Set back to idle after completion
            elseif state == 'q'
                println("Received quit signal, exiting")
                break
            end
            
            sleep(0.1)  # Small delay to avoid busy waiting
        end
    catch e
        println("Julia solver error: ", e)
        write_shared_state('e')
    finally
        println("Julia solver stopped")
    end
end

# Run main function
main()