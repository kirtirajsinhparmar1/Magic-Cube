#!/bin/bash
#SBATCH --job-name=onecube_img_gate
#SBATCH --output="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCubeImagingFinal/runtime/logs/gate_%A_%a.out"
#SBATCH --error="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCubeImagingFinal/runtime/logs/gate_%A_%a.err"
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=24:00:00
#SBATCH --array=0-3%4

set -euo pipefail

PROJECT_ROOT="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCubeImagingFinal"
PYTHON="/user/kmparmar/venv/bin/python"
cd "$PROJECT_ROOT"

if [[ -z "${IMAGING_STAGE:-}" || -z "${IMAGING_SHARD_COUNT:-}" ]]; then
    echo "IMAGING_STAGE and IMAGING_SHARD_COUNT must be provided by the orchestrator." >&2
    exit 2
fi

module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="$EBROOTGEANT4MINDATA"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2

if ! command -v Gate >/dev/null 2>&1; then
    echo "Preflight failed: Gate is missing from PATH after loading the validated environment." >&2
    exit 127
fi
env -u PYTHONPATH "$PYTHON" --version

env -u PYTHONPATH "$PYTHON" scripts/run_gate_shard.py \
    --stage "$IMAGING_STAGE" \
    --shard-index "$SLURM_ARRAY_TASK_ID" \
    --shard-count "$IMAGING_SHARD_COUNT"
