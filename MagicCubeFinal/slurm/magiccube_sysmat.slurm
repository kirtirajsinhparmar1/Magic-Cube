#!/usr/bin/env bash
#SBATCH --job-name=mcfinal_sysmat
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=../runtime/logs/sysmat_%j.out
#SBATCH --error=../runtime/logs/sysmat_%j.err
set -euo pipefail
ROOT="${MAGICCUBE_ROOT:?MAGICCUBE_ROOT is required}"
env -u PYTHONPATH /user/kmparmar/venv/bin/python "$ROOT/scripts/generate_sysmat.py" --manifest "${MAGICCUBE_MANIFEST:?}"
