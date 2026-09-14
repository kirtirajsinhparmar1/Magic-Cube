#!/bin/bash
#SBATCH --job-name=magiccube_step4
#SBATCH --cluster=ub-hpc
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=magiccube_step4_%j.out
#SBATCH --error=magiccube_step4_%j.err

set -euo pipefail

WORKDIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
RUNTIME_DIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step4"
PYTHON="/user/kmparmar/venv/bin/python"

cd "$WORKDIR"
mkdir -p "$RUNTIME_DIR"

# Match the module order used by the repository's established CCR scripts.
module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="${EBROOTGEANT4MINDATA}"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2

{
    echo "Magic-Cube Step-4 runtime environment"
    hostname
    date --iso-8601=seconds
    pwd
    module list 2>&1
    which Gate
    Gate --version 2>&1 || Gate --help 2>&1 || true
    command -v geant4-config || true
    geant4-config --version 2>&1 || true
    env | grep -E '^(G4|GEANT4|EBROOTGEANT4)' | sort || true
    "$PYTHON" --version
    env -u PYTHONPATH "$PYTHON" -c 'import uproot; print("uproot", uproot.__version__)'
} > "$RUNTIME_DIR/environment.txt" 2>&1

env -u PYTHONPATH "$PYTHON" validate_magiccube_geometry.py \
    > "$RUNTIME_DIR/static_geometry_validation.stdout" \
    2> "$RUNTIME_DIR/static_geometry_validation.stderr"

if Gate magiccube_runtime_geometry_check.mac \
    > "$RUNTIME_DIR/geometry_check.stdout" \
    2> "$RUNTIME_DIR/geometry_check.stderr"; then
    geometry_status=0
else
    geometry_status=$?
fi
printf '%s\n' "$geometry_status" > "$RUNTIME_DIR/geometry_check.exit_code"
if (( geometry_status != 0 )); then
    echo "Magic-Cube geometry-only initialization failed with exit code $geometry_status" >&2
    exit "$geometry_status"
fi

env -u PYTHONPATH "$PYTHON" run_magiccube_step4_runtime.py
env -u PYTHONPATH "$PYTHON" inspect_magiccube_runtime.py
env -u PYTHONPATH "$PYTHON" validate_magiccube_runtime.py

echo "Magic-Cube Step-4 runtime workflow completed."
