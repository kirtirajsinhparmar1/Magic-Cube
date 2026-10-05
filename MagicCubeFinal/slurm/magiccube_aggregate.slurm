#!/usr/bin/env bash
#SBATCH --job-name=mcfinal_matrix
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=../runtime/logs/full/matrix_%j.out
#SBATCH --error=../runtime/logs/full/matrix_%j.err
set -euo pipefail
ROOT="${MAGICCUBE_ROOT:?MAGICCUBE_ROOT is required}"
env -u PYTHONPATH /user/kmparmar/venv/bin/python "$ROOT/scripts/aggregate_system_matrix.py"
