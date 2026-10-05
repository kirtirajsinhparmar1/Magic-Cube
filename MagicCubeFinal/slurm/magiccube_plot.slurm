#!/usr/bin/env bash
#SBATCH --job-name=mcfinal_plot
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=../runtime/logs/plot_%j.out
#SBATCH --error=../runtime/logs/plot_%j.err
set -euo pipefail
ROOT="${MAGICCUBE_ROOT:?MAGICCUBE_ROOT is required}"
PY=/user/kmparmar/venv/bin/python
env -u PYTHONPATH "$PY" "$ROOT/scripts/plot_positions.py" --manifest "${MAGICCUBE_MANIFEST:?}" --detector-id "${MAGICCUBE_DETECTOR_ID:-0}"
env -u PYTHONPATH "$PY" "$ROOT/scripts/plot_system_matrix.py" --manifest "${MAGICCUBE_MANIFEST:?}" --detector-id "${MAGICCUBE_DETECTOR_ID:-0}"
