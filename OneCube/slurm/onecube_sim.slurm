#!/bin/bash
# OneCube simulation shard. Runtime execution is performed manually by the user.
#SBATCH --job-name=onecube_sim
#SBATCH --output="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube/runtime/logs/onecube_sim_%A_%a.out"
#SBATCH --error="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube/runtime/logs/onecube_sim_%A_%a.err"
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --array=0-0

set -euo pipefail

ONECUBE_ROOT="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube"
SIM_DIR="$ONECUBE_ROOT/runtime/sim"
LOG_DIR="$ONECUBE_ROOT/runtime/logs"

mkdir -p "$SIM_DIR" "$ONECUBE_ROOT/runtime/merged" "$LOG_DIR"
rm -f "$SIM_DIR"/onecube*.root
rm -f "$SIM_DIR/gate_exit_code.txt" "$LOG_DIR/gate.log" "$LOG_DIR/gate_preflight.log"

module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="$EBROOTGEANT4MINDATA"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2

cd "$ONECUBE_ROOT/GATE-Macro"
{
    hostname
    date
    pwd
    module list 2>&1
    which Gate
    Gate --version
    env -u PYTHONPATH /user/kmparmar/venv/bin/python --version
} > "$LOG_DIR/gate_preflight.log" 2>&1

set +e
Gate OneCube.mac > "$LOG_DIR/gate.log" 2>&1
gate_exit_code=$?
set -e

printf '%s\n' "$gate_exit_code" > "$SIM_DIR/gate_exit_code.txt"
if [[ "$gate_exit_code" -ne 0 ]]; then
    exit "$gate_exit_code"
fi
