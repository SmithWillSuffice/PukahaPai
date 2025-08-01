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

## Usage Tips

THe toml for Lorenz Attarctor is `./models/lorenz_attractor.toml`.

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
