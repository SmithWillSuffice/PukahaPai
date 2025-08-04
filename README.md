# PukahaPai
[![Development Status](https://img.shields.io/badge/Status-Alpha-orange)](https://yourprojecturl.com/docs/alpha-status) [![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)](https://www.python.org/) [![Julia](https://img.shields.io/badge/Julia-1.8+-purple?logo=julia&logoColor=white)](https://julialang.org/) [![Configuration](https://img.shields.io/badge/Config-TOML-gray?logo=toml&logoColor=white)](https://toml.io/) Your project description starts here...


This project is for a _future_ dearpygui app for interactively running (simple)
ODE system solvers. The aim is the graduate up to the complexity of an MMT
(sectoral balance) Minsky ODES. The preprocessing to generate an ODE toml spec
using Godley Tables is not yet ready.

However, you should be able to get the damped **pendulum** model working and the
**Lorenz Attractor**. If so, then you can build your own models using these
exemplars. It makes a fun school project for simple scientific computing. Python
for interface ease and Julia for fast numerics.

**Warning:** USE AT YOUR OWN RISK OF ANNOYANCE!

This project is not really for public use. See the file `README_pukahapai.md`
for development notes and progress.

## Installation

```bash
# Example installation steps
git clone [https://github.com/SmithWillSuffice/PukahaPai.git](https://github.com/SmithWillSuffice/PukahaPai.git)
cd PukahaPai
# TODO
# pip install -r requirements.txt (if applicable)
```
The requirements are not hard to install on GNU+Linux OS. Most come from PyPi,
or apt repositories. So there is no requirements.txt yet. Maybe later when the 
project is more user-friendly.

Julia packages:
* Start Julia: Open a terminal and type julia to start the Julia REPL (Read-Eval-Print Loop).
* Enter Package Mode: Press the `]` key in the Julia REPL to switch to the
  package manager mode. Your prompt will change from `julia>` to `pkg>`.
* Add the Packages: Type the following command to add both packages at once:
```julia
 add DifferentialEquations Sundials
```
or
```julia
import Pkg; Pkg.add("Sundials")  # etc.
```
* The package manager will download and install the packages and their dependencies. This may take a few minutes.
* Exit Package Mode: Press the backspace key to return to the regular julia>
  prompt.

The other packages you see in your this project: Mmap, Sockets, and
SharedArrays, are normally part of Julia's standard library, so they come
pre-installed with Julia itself and do not need to be added manually.


## Usage Tips

The toml for Lorenz Attarctor is `./models/lorenz_attractor.toml`.

**Warning** you cannot use a period `.` nor other special chars 
in the toml name, except `.toml` because it is used to generate 
Julia functions. Julia and python function names can have undrscores, but 
not periods nor other special characters!

For the Lorenz Attractor I would just run the cmdl version:
```bash
./generate_julia_odesolver.py lorenz_attractor
julia models/lorenz_attractor_cmdl.jl
./plots4model.py lorenz_attractor
```

## Solvers

Earlier I used the simple ODE solver 
```julia
prob = ODEProblem(ode!, u0, tspan)
```
but this is no good when some DE's depend upon the other derivatives. So I
switched to an algebraic solver,
```julia
prob = DAEProblem(dae!, du0, u0, tspan, differential_vars = [true, true, true, true])
```
which might run slower, but gives us more generality --- the cost of writing a
general purppose package you can say. THough I have not actually compared run
times.

## License

This project is Free Software: You can use, study, share and improve it at will.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

---

## Copyright

Copyright © 2025 Bijou M. Smith   
All rights reserved.
