#!/usr/bin/env bash
#SBATCH --job-name=mcfinal_ppdf
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=../runtime/logs/ppdf_%j.out
#SBATCH --error=../runtime/logs/ppdf_%j.err
set -euo pipefail
ROOT="${MAGICCUBE_ROOT:?MAGICCUBE_ROOT is required}"
env -u PYTHONPATH /user/kmparmar/venv/bin/python "$ROOT/scripts/generate_ppdf.py" --manifest "${MAGICCUBE_MANIFEST:?}"
