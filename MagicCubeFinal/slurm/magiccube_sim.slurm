#!/usr/bin/env bash
#SBATCH --job-name=mcfinal_sim
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=../runtime/logs/sim_%A_%a.out
#SBATCH --error=../runtime/logs/sim_%A_%a.err
set -euo pipefail
ROOT="${MAGICCUBE_ROOT:?MAGICCUBE_ROOT is required}"
PY=/user/kmparmar/venv/bin/python
MANIFEST="${MAGICCUBE_MANIFEST:?MAGICCUBE_MANIFEST is required}"
TASK_ID="${SLURM_ARRAY_TASK_ID:?array index required}"
MODE="${MAGICCUBE_MODE:-validation}"
if [[ "$MODE" == full ]]; then
    env -u PYTHONPATH "$PY" "$ROOT/scripts/record_full_task.py" --task-id "$TASK_ID"
    trap 'code=$?; env -u PYTHONPATH "$PY" "$ROOT/scripts/record_full_task.py" --task-id "$TASK_ID" --exit-code "$code"; exit "$code"' EXIT
fi
module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="${EBROOTGEANT4MINDATA}"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2
env -u PYTHONPATH "$PY" "$ROOT/scripts/render_gate_macro.py" --manifest "$MANIFEST" --task-id "$TASK_ID" --mode "$MODE"
if [[ "$MODE" == full ]]; then
    RUN_DIR="$ROOT/runtime/generated_macros/full/task_$(printf '%06d' "$TASK_ID")"
    GATE_LOG="$ROOT/runtime/logs/full/gate_${TASK_ID}.log"
    EXIT_MARKER="$ROOT/runtime/sim/full/task_$(printf '%06d' "$TASK_ID").exit_code.txt"
else
    RUN_DIR="$ROOT/runtime/generated_macros/task_$(printf '%06d' "$TASK_ID")"
    GATE_LOG="$ROOT/runtime/logs/gate_${TASK_ID}.log"
    EXIT_MARKER="$ROOT/runtime/sim/task_$(printf '%06d' "$TASK_ID").exit_code.txt"
fi
set +e
(cd "$RUN_DIR" && Gate main.mac) >"$GATE_LOG" 2>&1
code=$?
set -e
printf '%s\n' "$code" >"$EXIT_MARKER"
exit "$code"
