#!/bin/bash
#SBATCH --job-name=magiccube_visualization
#SBATCH --cluster=ub-hpc
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=magiccube_visualization_%j.out
#SBATCH --error=magiccube_visualization_%j.err

set -euo pipefail

WORKDIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
OUTDIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/visualization"

mkdir -p "$OUTDIR"

# Match the known-working UB CCR Step-4 environment.
module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2
export GEANT4_DATA_DIR="$EBROOTGEANT4MINDATA"
module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2

# Resolve all relative /control/execute and material-database references in OUTDIR.
cp -p "$WORKDIR/GateMaterials.db" "$OUTDIR/"
cp -p "$WORKDIR/magiccube_geometry.mac" "$OUTDIR/"
cp -p "$WORKDIR/magiccube_visualization.mac" "$OUTDIR/"
cp -p "$WORKDIR/magiccube_visualization_gagg_only.mac" "$OUTDIR/"

# Only old visualization-generated files in the dedicated output directory are removed.
rm -f "$OUTDIR"/g4_*.wrl
rm -f "$OUTDIR/magiccube_full.wrl"
rm -f "$OUTDIR/magiccube_gagg_only.wrl"

cd "$OUTDIR"

export_one() {
    macro="$1"
    final="$2"
    before="$OUTDIR/.$final.existing"
    selected=""

    find "$OUTDIR" -maxdepth 1 -type f -name 'g4_*.wrl' -printf '%p\n' | sort > "$before"
    echo "Starting VRML export: $macro"
    Gate "$macro"
    echo "GATE completed: $macro"

    while IFS= read -r candidate; do
        [[ -z "$candidate" ]] && continue
        if grep -Fqx "$candidate" "$before"; then
            continue
        fi
        if [[ -n "$selected" ]]; then
            echo "ERROR: more than one new g4_*.wrl file was produced for $macro" >&2
            rm -f "$before"
            exit 1
        fi
        selected="$candidate"
    done < <(find "$OUTDIR" -maxdepth 1 -type f -name 'g4_*.wrl' -printf '%p\n' | sort)

    rm -f "$before"
    if [[ -z "$selected" ]]; then
        echo "ERROR: no new g4_*.wrl file was produced for $macro" >&2
        exit 1
    fi
    mv -- "$selected" "$OUTDIR/$final"
    echo "Saved $OUTDIR/$final"
}

export_one magiccube_visualization.mac magiccube_full.wrl
export_one magiccube_visualization_gagg_only.mac magiccube_gagg_only.wrl

echo "Magic-Cube visualization exports complete."

