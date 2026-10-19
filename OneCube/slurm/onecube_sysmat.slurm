#!/bin/bash
# OneCube system-matrix stage. Runtime execution is performed manually by the user.
#SBATCH --job-name=onecube_sysmat
#SBATCH --output="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube/runtime/logs/onecube_sysmat_%j.out"
#SBATCH --error="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube/runtime/logs/onecube_sysmat_%j.err"
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00

set -euo pipefail
ONECUBE_ROOT="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube"
cd "$ONECUBE_ROOT"

env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/generate_sysmat.py
