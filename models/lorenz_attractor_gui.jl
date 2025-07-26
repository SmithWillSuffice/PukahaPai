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
    
    # Verify shared memory exists and has correct size
    if !isfile(shmpath)
        error("Shared memory file not found - is the GUI controller running?")
    elseif filesize(shmpath) != sz
        error("Shared memory size mismatch - please restart the GUI")
    end
    
    # Open with proper error handling
    fd = nothing
    try
        fd = open(shmpath, "r+")
        arr = Mmap.mmap(fd, Vector{UInt8}, sz)
        return arr, Ptr{lorenz_attractor_Shared}(pointer(arr))
    catch e
        fd !== nothing && close(fd)
        rethrow(e)
    end
end

function read_shared_params()
    arr, ptr = open_shared_lorenz_attractor()
    try
        return unsafe_load(ptr)
    finally
        finalize(arr)  # Clean up memory mapping
    end
end

function write_shared_state(new_state::Char)
    arr, ptr = open_shared_lorenz_attractor()
    try
        unsafe_store!(Ptr{UInt8}(pointer(arr)), UInt8(new_state))
    finally
        finalize(arr)
    end
end

function check_gui_state()
    arr, ptr = open_shared_lorenz_attractor()
    try
        state_byte = unsafe_load(Ptr{UInt8}(pointer(arr)))
        return Char(state_byte)
    finally
        finalize(arr)
    end
end


function solve_ode()
    # Read parameters from shared memory
    params = read_shared_params()
    csv_write_counter = 0
    csv_write_freq = 5  # Write every 5 steps
    
    function ode!(du, u, p, t)
    
        x = u[1]
    
        y = u[2]
    
        z = u[3]
    

        # Extract parameters from shared memory struct
    
            sigma = params.sigma
    
            rho = params.rho
    
            beta = params.beta
    

        # Auxiliary equations
    

        # ODEs
    
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
    
    # Single, properly defined step_callback function
    step_callback = function (integrator)
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
        csv_write_counter += 1
        if csv_write_counter % csv_write_freq == 0
            t = integrator.t
            y = integrator.u
            write(outfile, string(t))
            for val in y
                write(outfile, "," * string(val))
            end
            write(outfile, "\n")
            flush(outfile)
        end
        return false
    end
    
    # DON'T set state to 'r' here - let GUI control it
    cb = DiscreteCallback((u,t,integrator)->true, step_callback)
    
    try
        sol = solve(prob, Tsit5(), dt=dt, adaptive=false, callback=cb)
        println("Simulation completed successfully")

        # Write final point if needed
        try
            t_final = sol.t[end]
            y_final = sol.u[end]
            write(outfile, string(t_final))
            for val in y_final
                write(outfile, "," * string(val))
            end
            write(outfile, "\n")
            flush(outfile)
        catch e
            println("Warning: Failed to write final CSV row: ", e)
        end

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
    
    try
        # Create exit condition flag
        exit_requested = Ref{Bool}(false)
        
        # Set up signal handler
        Base.exit_on_sigint(false)
        ccall(:jl_exit_on_sigint, Cvoid, (Cint,), 0)
        
        while !exit_requested[]
            state = check_gui_state()
            
            if state == 'r'
                println("Starting simulation...")
                solve_ode()
                write_shared_state('s')  # Completed normally
            elseif state == 'q'
                println("Received quit signal")
                exit_requested[] = true
                break
            end
            
            sleep(0.1)
        end
    catch e
        println("Julia solver error: ", e)
        write_shared_state('e')
    finally
        println("Julia solver cleanly stopped")
        try
            write_shared_state('s')  # Ensure final state
        catch
            println("Final state write failed")
        end
    end
end

# Run main function
main()