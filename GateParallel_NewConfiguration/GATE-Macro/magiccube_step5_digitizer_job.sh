#!/usr/bin/env bash
# Manual-only Slurm wrapper for the bounded Step-5 digitizer check.
# Codex must not submit this job; run it manually on UB CCR after reviewing
# the preparation validator and this runbook.
#SBATCH --cluster=ub-hpc
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --job-name=magiccube-step5-dig
#SBATCH --time=00:10:00
# Slurm opens these files before the script runs; use the existing parent
# directory because the script creates the step5 subdirectory below.
#SBATCH --output=magiccube_step5_%j.out
#SBATCH --error=magiccube_step5_%j.err

set -euo pipefail

WORKDIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
RUNTIME_DIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5"
PYTHON="/user/kmparmar/venv/bin/python"

mkdir -p "$RUNTIME_DIR"
cd "$WORKDIR"

module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="${EBROOTGEANT4MINDATA}"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2

set +e
Gate magiccube_step5_digitizer_check.mac > "$RUNTIME_DIR/magiccube_step5_digitizer_gate.log" 2>&1
gate_status=$?
set -e

printf '%s\n' "$gate_status" > "$RUNTIME_DIR/magiccube_step5_gate.exit_code"

"$PYTHON" validate_magiccube_step5_outputs.py \
  --output-dir "$RUNTIME_DIR" \
  --gate-exit-code "$gate_status"
