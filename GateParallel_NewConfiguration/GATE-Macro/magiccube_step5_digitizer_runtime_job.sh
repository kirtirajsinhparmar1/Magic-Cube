#!/bin/bash
#SBATCH --job-name=magiccube_step5_digitizer
#SBATCH --cluster=ub-hpc
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=magiccube_step5_digitizer_%j.out
#SBATCH --error=magiccube_step5_digitizer_%j.err

set -u

WORKDIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
OUTPUT_DIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_digitizer"
PYTHON="/user/kmparmar/venv/bin/python"

mkdir -p "$OUTPUT_DIR"
rm -f \
  "$OUTPUT_DIR/gate.log" \
  "$OUTPUT_DIR/gate_exit_code.txt" \
  "$OUTPUT_DIR/environment.txt" \
  "$OUTPUT_DIR"/magiccube_step5_digitizer*.root

module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="${EBROOTGEANT4MINDATA}"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2

{
  echo "WORKDIR=$WORKDIR"
  echo "OUTPUT_DIR=$OUTPUT_DIR"
  echo "PYTHON=$PYTHON"
  module list
  command -v Gate || true
} > "$OUTPUT_DIR/environment.txt" 2>&1

cd "$WORKDIR"
Gate "$WORKDIR/magiccube_step5_digitizer_runtime_check.mac" \
  > "$OUTPUT_DIR/gate.log" 2>&1
gate_status=$?
printf '%s\n' "$gate_status" > "$OUTPUT_DIR/gate_exit_code.txt"

env -u PYTHONPATH "$PYTHON" \
  "$WORKDIR/validate_magiccube_step5_digitizer_runtime_outputs.py" \
  --output-dir "$OUTPUT_DIR"
validator_status=$?

if [ "$gate_status" -ne 0 ]; then
  exit "$gate_status"
fi
exit "$validator_status"
