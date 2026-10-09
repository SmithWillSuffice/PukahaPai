# Julia Solvers README

`ODE` and `DAE` are problem classes; 

## ODE: ordinary differential equation

An ordinary differential equation has the familiar explicit form
$$
\frac{du}{dt}=f(u,p,t).
$$

In SciML/DifferentialEquations.jl, this is represented by an `ODEProblem`. 
The current documentation also allows a mass-matrix form
$$
M\frac{du}{dt}=f(u,p,t),
$$
with the ordinary explicit ODE recovered when $M=I$. [SCIML Documentation](https://docs.sciml.ai/DiffEqDocs/v7.17/types/ode_types/)

A typical Julia definition is

```julia
function rhs!(du, u, p, t)
    du[1] = ...
    du[2] = ...
end

prob = ODEProblem(rhs!, u0, tspan)
```

The important point is that, given $u$ and $t$, the equations directly 
determine $\dot u$.

For an ordinary pendulum or the Lorenz equations, this is exactly the 
natural mathematical form. There is no benefit in disguising them as DAEs.

Once you have an `ODEProblem`, you still have to choose an integration 
algorithm. Examples include

```julia
Tsit5()
RK4()
Vern7()
Rodas5P()
```

and many others. These are numerical methods, not alternative meanings 
of “ODE”.

### DAE: differential-algebraic equation

A DAE is more general. SciML represents a fully implicit DAE in the form

$$
0=F(\dot u,u,p,t).
$$

That is what `DAEProblem` means. [Again, see: SCIML Documentation](https://docs.sciml.ai/DiffEqDocs/stable/types/dae_types/)

In Julia, the residual function looks like

```julia
function residual!(resid, du, u, p, t)
    resid[1] = ...
    resid[2] = ...
end

prob = DAEProblem(
    residual!,
    du0,
    u0,
    tspan
)
```
The crucial difference is that the equations do not necessarily solve 
directly for every component of $\dot u$.

For example, suppose
$$
\dot x=v,
$$
but another variable is constrained algebraically by
$$
x^2+y^2=1.
$$
Then $y$ is not governed by its own ordinary evolution law; it must 
satisfy a constraint at every time. That is naturally a DAE.

A schematic DAE might therefore be
$$
\begin{aligned}
\dot x-v  &=0,\\\\
x^2+y^2-1 &=0.
\end{aligned}
$$
The second equation contains no derivative at all.

This is why DAEs occur naturally in constrained mechanics, circuits, 
chemical-equilibrium systems, power systems, incompressibility constraints, 
and many coupled engineering models.

There is also an intermediate representation called a mass-matrix system,
$$
M\dot u=f(u,t),
$$

where $M$ may be singular. SciML treats many such systems through 
`ODEProblem` with a mass matrix, while fully implicit systems 
use `DAEProblem`. The current solver documentation explicitly 
distinguishes mass-matrix DAEs from fully implicit DAEs.

### IDA: a particular DAE solver

`IDA` is not another equation type. It is an algorithm supplied by 
the Sundials library for solving fully implicit DAEs.

SciML describes `Sundials.IDA` as a fixed-leading-coefficient, fully 
implicit BDF method, and recommends it as a general solver for fully 
implicit `Float64` DAEs.

So:

```julia
prob = DAEProblem(...)
sol = solve(prob, Sundials.IDA())
```
means:

- `DAEProblem` describes the mathematics;
- `IDA()` chooses the numerical algorithm.

IDA uses a BDF — backward differentiation formula — family of implicit 
multistep methods. Because it is implicit, each step generally involves 
solving nonlinear equations, typically with Newton-type iterations and 
a linear solver internally. That extra work is why using IDA on a simple 
explicit pendulum was unnecessary overhead.

Also, with current DifferentialEquations.jl releases, Sundials is not 
automatically loaded merely by
```julia
using DifferentialEquations
```
so IDA requires the Sundials package explicitly. 

### Where `Tsit5` fits

`Tsit5` sits at the same conceptual level as `IDA`, not at the same 
level as `ODEProblem`.

For example:
```julia
prob = ODEProblem(rhs!, u0, tspan)
sol = solve(prob, Tsit5())
```
means:
- `ODEProblem`: explicit ODE mathematical problem;
- `Tsit5()`: numerical integration algorithm.

Whereas:
```julia
prob = DAEProblem(residual!, du0, u0, tspan)
sol = solve(prob, Sundials.IDA())
```
means:
- `DAEProblem`: fully implicit DAE mathematical problem;
- `IDA()`: numerical integration algorithm.

### A useful hierarchy

I would summarize it as:

```
Mathematical problem
│
├── ODEProblem
│     du/dt = f(u,p,t)
│
│     possible solvers:
│       Tsit5
│       RK4
│       Vern7
│       Rodas5P
│       ...
│
└── DAEProblem
      0 = F(du,u,p,t)

      possible solvers:
        IDA
        DFBDF
        DABDF2
        ...
```

There is also the mass-matrix route:
```
ODEProblem with mass matrix
    M du/dt = f(u,p,t)
```

which overlaps mathematically with some DAEs.

A  taxonomy is:

- `ODEProblem`:--- ordinary differential-equation problem;
- `DAEProblem`:--- fully implicit differential-algebraic problem;
- `Tsit5`, `IDA`, `Rodas5P`, `RK4`, etc.:--- numerical algorithms chosen 
to solve suitable problem types.

And beyond ODE/DAE, SciML has many other problem classes — SDEs, 
delay equations, boundary-value problems, jump processes, steady-state 
problems, second-order/dynamical ODEs, and so forth. 
DifferentialEquations.jl explicitly documents these as separate problem 
types.

For **PukahaPai** specifically, I would state the policy as:

> If the TOML supplies ordinary evolution laws
$$
  dx_i/dt = f_i(x,t),
$$
generate an ODEProblem. <br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;If the model genuinely contains 
algebraic constraints or equations that cannot be solved explicitly for 
all state derivatives, generate a DAEProblem.<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
The selected solver method is then chosen independently subject to
compatibility with that problem type.

