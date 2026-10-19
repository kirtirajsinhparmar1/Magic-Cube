#!/bin/bash
# OneCube ROOT merge stage. Runtime execution is performed manually by the user.
#SBATCH --job-name=onecube_merge
#SBATCH --output="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube/runtime/logs/onecube_merge_%j.out"
#SBATCH --error="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube/runtime/logs/onecube_merge_%j.err"
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00

set -euo pipefail

ONECUBE_ROOT="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube"
SIM_DIR="$ONECUBE_ROOT/runtime/sim"
MERGED_DIR="$ONECUBE_ROOT/runtime/merged"

cd "$ONECUBE_ROOT"
mkdir -p "$MERGED_DIR"

[[ -s "$SIM_DIR/gate_exit_code.txt" ]]
[[ "$(tr -d '[:space:]' < "$SIM_DIR/gate_exit_code.txt")" == "0" ]]

module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="$EBROOTGEANT4MINDATA"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2

mapfile -t hit_inputs < <(find "$SIM_DIR" -maxdepth 1 -type f -iname '*hits*.root' -size +100c -print | sort)
mapfile -t singles_inputs < <(find "$SIM_DIR" -maxdepth 1 -type f -iname '*singles*.root' -size +100c -print | sort)

if (( ${#hit_inputs[@]} == 0 )); then
    echo "No non-empty Hits ROOT input found" >&2
    exit 1
fi
if (( ${#singles_inputs[@]} == 0 )); then
    echo "No non-empty Singles ROOT input found" >&2
    exit 1
fi

rm -f "$MERGED_DIR/hits.root" "$MERGED_DIR/singles.root"
hadd -f "$MERGED_DIR/hits.root" "${hit_inputs[@]}"
hadd -f "$MERGED_DIR/singles.root" "${singles_inputs[@]}"

[[ -s "$MERGED_DIR/hits.root" ]]
[[ -s "$MERGED_DIR/singles.root" ]]
(( $(stat -c '%s' "$MERGED_DIR/hits.root") > 100 ))
(( $(stat -c '%s' "$MERGED_DIR/singles.root") > 100 ))
