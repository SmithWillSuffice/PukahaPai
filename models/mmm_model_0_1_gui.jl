# -*- coding: utf-8 -*-
# mmm_model_0.1.jl  - for GUI slaving
using DifferentialEquations
import Base.Libc
using Mmap


# Auto-generated struct for shared memory interop
struct mmm_model_0_1_Shared
    state::UInt8
    t0::Float64
    t1::Float64
    N0::Float64
    K0::Float64
    c_u::Float64
    nu::Float64
    alpha::Float64
    beta::Float64
    id::Float64
    monopoly::Float64
    s::Float64
    Phi_d::Float64
    Phi_c::Float64
    gamma_p::Float64
    deprec::Float64
    ai::Float64
    bi::Float64
    ci::Float64
    di::Float64
    gamma_i::Float64
end

function open_shared_mmm_model_0_1()
    shmpath = "/dev/shm/pukaha_shared"
    sz = sizeof(mmm_model_0_1_Shared)
    
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
        return arr, Ptr{mmm_model_0_1_Shared}(pointer(arr))
    catch e
        fd !== nothing && close(fd)
        rethrow(e)
    end
end

function read_shared_params()
    arr, ptr = open_shared_mmm_model_0_1()
    try
        return unsafe_load(ptr)
    finally
        finalize(arr)  # Clean up memory mapping
    end
end

function write_shared_state(new_state::Char)
    arr, ptr = open_shared_mmm_model_0_1()
    try
        unsafe_store!(Ptr{UInt8}(pointer(arr)), UInt8(new_state))
    finally
        finalize(arr)
    end
end

function check_gui_state()
    arr, ptr = open_shared_mmm_model_0_1()
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
    
        P = u[1]
    
        D = u[2]
    
        u = u[3]
    
        lambda = u[4]
    

        # Extract parameters from shared memory struct
    
            N0 = params.N0
    
            K0 = params.K0
    
            c_u = params.c_u
    
            nu = params.nu
    
            alpha = params.alpha
    
            beta = params.beta
    
            id = params.id
    
            monopoly = params.monopoly
    
            s = params.s
    
            Phi_d = params.Phi_d
    
            Phi_c = params.Phi_c
    
            gamma_p = params.gamma_p
    
            deprec = params.deprec
    
            ai = params.ai
    
            bi = params.bi
    
            ci = params.ci
    
            di = params.di
    
            gamma_i = params.gamma_i
    

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
    
    u0 = [
    
            1.0,
    
            50.0,
    
            0.6,
    
            0.9
    
    ]
    
    tspan = (params.t0, params.t1)
    dt = 0.1
    prob = ODEProblem(ode!, u0, tspan)
    outfile = open("models/mmm_model_0.1.csv", "w")
    write(outfile, "t,P,D,u,lambda\n")
    
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
    println("Julia solver started for mmm_model_0.1")
    
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