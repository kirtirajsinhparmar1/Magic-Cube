#!/bin/bash
#SBATCH --job-name=magiccube_step7
#SBATCH --cluster=ub-hpc
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=magiccube_step7_%j.out
#SBATCH --error=magiccube_step7_%j.err

set -uo pipefail

WORKDIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
OUTPUT_DIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step7"
PYTHON="/user/kmparmar/venv/bin/python"

mkdir -p "$OUTPUT_DIR"

# Clean only artifacts owned by this bounded Step-7 run.  Production ROOT
# files are deliberately not removed here; preparation blocks collisions.
rm -f \
  "$OUTPUT_DIR/gate.log" \
  "$OUTPUT_DIR/gate_exit_code.txt" \
  "$OUTPUT_DIR/environment.txt" \
  "$OUTPUT_DIR/validator.log" \
  "$OUTPUT_DIR/step7_root_schema.txt"

# The bounded output prefix is unique to this validation run.  Remove only
# prior files produced by that prefix; never remove production-prefix files.
rm -f "$WORKDIR"/magiccube_step7_bounded*.root

if ! cd "$WORKDIR"; then
  printf '%s\n' 'Unable to cd to the explicit Step-7 work directory.' >&2
  exit 2
fi

module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="${EBROOTGEANT4MINDATA:-}"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2

{
  printf 'WORKDIR=%s\n' "$WORKDIR"
  printf 'OUTPUT_DIR=%s\n' "$OUTPUT_DIR"
  printf 'HOSTNAME=%s\n' "$(hostname)"
  printf 'DATE=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'GATE_PATH=%s\n' "$(command -v Gate 2>/dev/null || true)"
  module list 2>&1 || true
} > "$OUTPUT_DIR/environment.txt"

# This is the single and only GATE invocation in the bounded Step-7 job.
Gate magiccube_step7_bounded_main.mac > "$OUTPUT_DIR/gate.log" 2>&1
gate_status=$?
printf '%s\n' "$gate_status" > "$OUTPUT_DIR/gate_exit_code.txt"

# The validator is deliberately separate from GATE.  Its status is useful for
# the handoff, but a nonzero GATE status remains authoritative.
env -u PYTHONPATH "$PYTHON" validate_magiccube_step7_outputs.py \
  --output-dir "$OUTPUT_DIR" \
  --production-dir "$WORKDIR" > "$OUTPUT_DIR/validator.log" 2>&1
validator_status=$?

if [ "$gate_status" -ne 0 ]; then
  exit "$gate_status"
fi
exit "$validator_status"
