#!/bin/bash
# Bounded Step-5 raw-Hits diagnostic job. The user runs this manually.
# The two Gate invocations are deliberately independent and sequential.
#SBATCH --job-name=magiccube_step5_hits
#SBATCH --cluster=ub-hpc
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=magiccube_step5_hits_%j.out
#SBATCH --error=magiccube_step5_hits_%j.err

set -u

WORKDIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
OUTPUT_DIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_hits"
PYTHON="/user/kmparmar/venv/bin/python"

cd "$WORKDIR" || exit 2
mkdir -p "$OUTPUT_DIR"

# Remove only this diagnostic's bounded artifacts. No production or frozen
# project files are touched.
rm -f \
    "$OUTPUT_DIR/internal_gate.log" \
    "$OUTPUT_DIR/internal_gate_exit_code.txt" \
    "$OUTPUT_DIR/external_gate.log" \
    "$OUTPUT_DIR/external_gate_exit_code.txt" \
    "$OUTPUT_DIR"/magiccube_step5_hits_internal*.root \
    "$OUTPUT_DIR"/magiccube_step5_hits_external*.root

module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="${EBROOTGEANT4MINDATA}"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2

set +e
Gate "$WORKDIR/magiccube_step5_hits_internal.mac" \
    > "$OUTPUT_DIR/internal_gate.log" 2>&1
INTERNAL_EXIT=$?
printf '%s\n' "$INTERNAL_EXIT" > "$OUTPUT_DIR/internal_gate_exit_code.txt"

Gate "$WORKDIR/magiccube_step5_hits_external.mac" \
    > "$OUTPUT_DIR/external_gate.log" 2>&1
EXTERNAL_EXIT=$?
printf '%s\n' "$EXTERNAL_EXIT" > "$OUTPUT_DIR/external_gate_exit_code.txt"

# The validator is independent of Gate. A NumPy/uproot environment problem
# is reported separately from the authoritative Gate exit codes and logs.
env -u PYTHONPATH "$PYTHON" \
    "$WORKDIR/validate_magiccube_step5_hits_outputs.py" \
    --output-dir "$OUTPUT_DIR"
VALIDATOR_EXIT=$?
set -e

echo "Internal Gate exit code: $INTERNAL_EXIT"
echo "External Gate exit code: $EXTERNAL_EXIT"
echo "Output-validator exit code: $VALIDATOR_EXIT"

if [ "$INTERNAL_EXIT" -ne 0 ]; then
    exit "$INTERNAL_EXIT"
fi
if [ "$EXTERNAL_EXIT" -ne 0 ]; then
    exit "$EXTERNAL_EXIT"
fi
exit "$VALIDATOR_EXIT"
