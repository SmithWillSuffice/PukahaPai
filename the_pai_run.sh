#!/bin/bash
# Run the four main PukahaPai scripts on a model

model=$1

cmd1="python3 generate_julia_odesolver.py ${model}" 
echo -e "Running:\n${cmdl}"
cmd1

cmd1="julia models/${model}_cmdl.jl"
echo -e "Running:\n${cmdl}"
echo "(this can take a while)"
cmd1

cmd1=python3 plots4model.py ${model}
echo -e "Running:\n${cmdl}"
cmd1

cmd1="xdg-open models/${model}.html"
echo -e "Opening report in browser:\n${cmdl}"
cmd1
