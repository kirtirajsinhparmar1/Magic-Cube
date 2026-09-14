#!/bin/bash
#SBATCH --job-name=magiccube_step5_system
#SBATCH --cluster=ub-hpc
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=magiccube_step5_system_%j.out
#SBATCH --error=magiccube_step5_system_%j.err

set -u

WORKDIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
OUTPUT_DIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_system"
GATE_LOG="$OUTPUT_DIR/magiccube_step5_system_gate.log"
EXIT_FILE="$OUTPUT_DIR/gate_exit_code.txt"
PYTHON="/user/kmparmar/venv/bin/python"

cd "$WORKDIR" || exit 2
mkdir -p "$OUTPUT_DIR"

rm -f \
    "$GATE_LOG" \
    "$EXIT_FILE" \
    "$OUTPUT_DIR/validation_summary.txt" \
    "$OUTPUT_DIR"/*.root

# Use the exact CCR module setup already validated by successful Step 4.
module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="${EBROOTGEANT4MINDATA}"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2

{
    echo "Magic-Cube Step-5 production-system runtime environment"
    hostname
    date --iso-8601=seconds
    pwd
    module list 2>&1
    which Gate
    Gate --version 2>&1 || Gate --help 2>&1 || true
    "$PYTHON" --version
    env -u PYTHONPATH "$PYTHON" -c \
        'import uproot; print("uproot", uproot.__version__)' || true
} > "$OUTPUT_DIR/environment.txt" 2>&1

set +e
Gate "$WORKDIR/magiccube_step5_system_check.mac" \
    > "$GATE_LOG" 2>&1
GATE_EXIT=$?
set -e

printf '%s\n' "$GATE_EXIT" > "$EXIT_FILE"

echo "Gate exit code: $GATE_EXIT"

# Validate separately. A Python-environment problem must not hide the
# authoritative Gate exit code.
set +e
env -u PYTHONPATH "$PYTHON" \
    "$WORKDIR/validate_magiccube_step5_system_outputs.py" \
    --output-dir "$OUTPUT_DIR" \
    --gate-exit-code "$GATE_EXIT"
VALIDATOR_EXIT=$?
set -e

echo "Validator exit code: $VALIDATOR_EXIT"

if [ "$GATE_EXIT" -ne 0 ]; then
    echo "GATE runtime failed with exit code $GATE_EXIT" >&2
    exit "$GATE_EXIT"
fi

exit "$VALIDATOR_EXIT"
