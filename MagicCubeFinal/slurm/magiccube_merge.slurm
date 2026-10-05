#!/usr/bin/env bash
#SBATCH --job-name=mcfinal_merge
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=../runtime/logs/merge_%j.out
#SBATCH --error=../runtime/logs/merge_%j.err
set -euo pipefail
ROOT="${MAGICCUBE_ROOT:?MAGICCUBE_ROOT is required}"
module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="${EBROOTGEANT4MINDATA}"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2
env -u PYTHONPATH /user/kmparmar/venv/bin/python "$ROOT/scripts/merge_runtime_outputs.py" --manifest "${MAGICCUBE_MANIFEST:?}"
