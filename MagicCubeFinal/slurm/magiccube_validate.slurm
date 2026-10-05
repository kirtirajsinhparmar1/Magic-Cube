#!/usr/bin/env bash
#SBATCH --job-name=mcfinal_validate
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=../runtime/logs/validate_%j.out
#SBATCH --error=../runtime/logs/validate_%j.err
set -euo pipefail
ROOT="${MAGICCUBE_ROOT:?MAGICCUBE_ROOT is required}"
env -u PYTHONPATH /user/kmparmar/venv/bin/python "$ROOT/scripts/validate_runtime.py" --mode "${MAGICCUBE_MODE:?}"
