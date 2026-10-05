#!/usr/bin/env bash
#SBATCH --job-name=mcfinal_heatmap
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --output=../runtime/logs/full/heatmap_%A_%a.out
#SBATCH --error=../runtime/logs/full/heatmap_%A_%a.err
set -euo pipefail
ROOT="${MAGICCUBE_ROOT:?MAGICCUBE_ROOT is required}"
env -u PYTHONPATH /user/kmparmar/venv/bin/python "$ROOT/scripts/plot_full_response.py" --plot-index "${SLURM_ARRAY_TASK_ID:?}"
