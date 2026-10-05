#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=/user/kmparmar/venv/bin/python
env -u PYTHONPATH "$PY" "$ROOT/scripts/generate_source_positions.py" --mode validation
env -u PYTHONPATH "$PY" "$ROOT/scripts/generate_simulation_manifest.py" --mode validation
MANIFEST="$ROOT/runtime/manifests/simulation_manifest_validation.csv"
N=$(env -u PYTHONPATH "$PY" -c 'import csv,sys; print(sum(1 for _ in csv.DictReader(open(sys.argv[1], newline=""))))' "$MANIFEST")
(( N > 0 ))
export MAGICCUBE_MANIFEST="$MANIFEST" MAGICCUBE_MODE=validation
sim=$(sbatch --parsable --array="0-$((N-1))" --export="ALL,MAGICCUBE_ROOT=$ROOT,MAGICCUBE_MANIFEST=$MANIFEST" "$ROOT/slurm/magiccube_sim.slurm")
merge=$(sbatch --parsable --dependency="afterok:$sim" --export="ALL,MAGICCUBE_ROOT=$ROOT,MAGICCUBE_MANIFEST=$MANIFEST" "$ROOT/slurm/magiccube_merge.slurm")
ppdf=$(sbatch --parsable --dependency="afterok:$merge" --export="ALL,MAGICCUBE_ROOT=$ROOT,MAGICCUBE_MANIFEST=$MANIFEST" "$ROOT/slurm/magiccube_ppdf.slurm")
sysmat=$(sbatch --parsable --dependency="afterok:$merge" --export="ALL,MAGICCUBE_ROOT=$ROOT,MAGICCUBE_MANIFEST=$MANIFEST" "$ROOT/slurm/magiccube_sysmat.slurm")
plot=$(sbatch --parsable --dependency="afterok:$ppdf:$sysmat" --export="ALL,MAGICCUBE_ROOT=$ROOT,MAGICCUBE_MANIFEST=$MANIFEST" "$ROOT/slurm/magiccube_plot.slurm")
validate=$(sbatch --parsable --dependency="afterok:$plot" --export="ALL,MAGICCUBE_ROOT=$ROOT,MAGICCUBE_MODE=validation" "$ROOT/slurm/magiccube_validate.slurm")
printf 'sim=%s merge=%s ppdf=%s sysmat=%s plot=%s validate=%s\n' "$sim" "$merge" "$ppdf" "$sysmat" "$plot" "$validate"
