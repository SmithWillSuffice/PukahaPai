# -*- coding: utf-8 -*-
# mmm_model_0_2.jl  - for GUI slaving
using DifferentialEquations
import Base.Libc
using Mmap


# Auto-generated struct for shared memory interop
struct mmm_model_0_2_Shared
    state::UInt8
    t0::Float64
    t1::Float64
    N0::Float64
    A0::Float64
    K0::Float64
    tau_P::Float64
    cG::Float64
    varpi::Float64
    nu::Float64
    alpha::Float64
    beta::Float64
    iG::Float64
    rT::Float64
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

function open_shared_mmm_model_0_2()
    shmpath = "/dev/shm/pukaha_shared"
    sz = sizeof(mmm_model_0_2_Shared)
    if !isfile(shmpath)
        error("Shared memory file not found - is the GUI controller running?")
    elseif filesize(shmpath) != sz
        error("Shared memory size mismatch - please restart the GUI")
    end
    fd = nothing
    try
        fd = open(shmpath, "r+")
        arr = Mmap.mmap(fd, Vector{UInt8}, sz)
        return arr, Ptr{mmm_model_0_2_Shared}(pointer(arr))
    catch e
        fd !== nothing && close(fd)
        rethrow(e)
    end
end

function read_shared_params()
    arr, ptr = open_shared_mmm_model_0_2()
    try
        return unsafe_load(ptr)
    finally
        finalize(arr)
    end
end

function write_shared_state(new_state::Char)
    arr, ptr = open_shared_mmm_model_0_2()
    try
        unsafe_store!(Ptr{UInt8}(pointer(arr)), UInt8(new_state))
    finally
        finalize(arr)
    end
end

function check_gui_state()
    arr, ptr = open_shared_mmm_model_0_2()
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
    
    function ode!(df, f, p, t)
    
        P = f[1]
    
        D = f[2]
    
        u = f[3]
    
        lambda = f[4]
    

        # Extract parameters from shared memory struct
    
            N0 = params.N0
    
            A0 = params.A0
    
            K0 = params.K0
    
            tau_P = params.tau_P
    
            cG = params.cG
    
            varpi = params.varpi
    
            nu = params.nu
    
            alpha = params.alpha
    
            beta = params.beta
    
            iG = params.iG
    
            rT = params.rT
    
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
    
        Y = Yr * P
    
        L = lambda * N
    
        K = nu * Y
    
        G = cG * Y
    
        T = rT * Y
    
        Phi = Phi_d/(1 - lambda)^gamma_p - Phi_c
    
        Gamma = (1 - u)/nu - deprec
    
        Pi = Y - u*A*L + iG * D
    
        pi = Pi/K
    
        Inv = ai / (bi + ci * pi)^gamma_i - di
    
        S = G - T + Inv * Y
    
    

        # Compute derivatives (for potential cross-referencing)
    
        f_P = tau_P * (u/(1 - monopoly) - P)
    
        f_D = G - T
    
        f_u = u * (Phi + varpi * f_lambda / lambda  + f_P / P - alpha)
    
        f_lambda = lambda * ( Gamma - deprec - alpha - beta )
    
    
        # Assign derivatives to output vector
    
        df[1] = f_P
    
        df[2] = f_D
    
        df[3] = f_u
    
        df[4] = f_lambda
    

end
    
    f0 = [
    
            1.0,
    
            50.0,
    
            0.6,
    
            0.9
    
    ]
    
    tspan = (params.t0, params.t1)
    dt = 0.1
    prob = ODEProblem(ode!, f0, tspan)
    outfile = open("models/mmm_model_0_2.csv", "w")
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
    cb = DiscreteCallback((f,t,integrator)->true, step_callback)
    
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
    println("Julia solver started for mmm_model_0_2")
    
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