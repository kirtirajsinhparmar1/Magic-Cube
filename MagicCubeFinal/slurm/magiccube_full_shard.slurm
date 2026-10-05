#!/usr/bin/env bash
#SBATCH --job-name=mcfinal_shard
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --output=../runtime/logs/full/shard_%A_%a.out
#SBATCH --error=../runtime/logs/full/shard_%A_%a.err
set -euo pipefail
ROOT="${MAGICCUBE_ROOT:?MAGICCUBE_ROOT is required}"
PY=/user/kmparmar/venv/bin/python
MANIFEST="${MAGICCUBE_MANIFEST:?MAGICCUBE_MANIFEST is required}"
SHARD_ID="${SLURM_ARRAY_TASK_ID:?array index required}"
SHARDS=$(env -u PYTHONPATH "$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["full_worker_shards"])' "$ROOT/config/production_config.json")
module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="${EBROOTGEANT4MINDATA}"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2
if ! command -v Gate; then
    echo "ERROR: Gate executable unavailable after loading the validated Gate/Geant4/OpenMPI environment." >&2
    exit 1
fi
if ! Gate --version; then
    echo "ERROR: Gate availability preflight failed after loading the validated Gate/Geant4/OpenMPI environment." >&2
    exit 1
fi
exec env -u PYTHONPATH "$PY" "$ROOT/scripts/run_full_shard.py" --manifest "$MANIFEST" --shard-id "$SHARD_ID" --shards "$SHARDS"
