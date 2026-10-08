#!/bin/bash
#
# Refresh PukahaPai project tar.gz archive
#
# Run from the project base dir (the one archived as "PukahaPai/").

set -euo pipefail
base=$(basename "$PWD")
out="../PukahaPai.tar.gz"

tar --format=ustar \
    --transform="s,^,$base/," \
    -czf "$out" \
    docs dpg_utils models templates tests \
    archive_stuff.sh Copilot_history.md copilot_prompts.md \
    generate_julia_odesolver.py godley_check.py \
    init LICENSE odemodel2tex.py ohp_copy.sh \
    plots4model.py plot_utils.py pukahaPai.py \
    README.md README_pukahapai.html README_pukahapai.md \
    stability.py style.css tomllib
