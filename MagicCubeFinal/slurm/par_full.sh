#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=/user/kmparmar/venv/bin/python
env -u PYTHONPATH "$PY" "$ROOT/scripts/generate_source_positions.py" --mode full
env -u PYTHONPATH "$PY" "$ROOT/scripts/generate_simulation_manifest.py" --mode full
env -u PYTHONPATH "$PY" "$ROOT/scripts/prepare_full_run.py"
MANIFEST="$ROOT/runtime/manifests/simulation_manifest_full.csv"
N=$(env -u PYTHONPATH "$PY" -c 'import csv,sys; print(sum(1 for _ in csv.DictReader(open(sys.argv[1], newline=""))))' "$MANIFEST")
P=$(env -u PYTHONPATH "$PY" -c 'import csv,sys; print(sum(1 for _ in csv.DictReader(open(sys.argv[1], newline=""))))' "$ROOT/runtime/manifests/plot_manifest_full.csv")
SHARDS=$(env -u PYTHONPATH "$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["full_worker_shards"])' "$ROOT/config/production_config.json")
WORKER_WALLTIME=$(env -u PYTHONPATH "$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["full_worker_walltime"])' "$ROOT/config/production_config.json")
PLOT_CAP=$(env -u PYTHONPATH "$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["full_array_max_concurrent"])' "$ROOT/config/production_config.json")
(( N > 0 && P > 0 && SHARDS > 0 && SHARDS <= N && PLOT_CAP > 0 ))
export MAGICCUBE_ROOT="$ROOT" MAGICCUBE_MANIFEST="$MANIFEST" MAGICCUBE_MODE=full
EXPORT="ALL,MAGICCUBE_ROOT,MAGICCUBE_MANIFEST,MAGICCUBE_MODE"
# Submission location also keeps the existing workers' relative log paths local.
cd "$ROOT/slurm"
sim=$(sbatch --parsable --array="0-$((SHARDS-1))" --time="$WORKER_WALLTIME" --export="$EXPORT" --output="$ROOT/runtime/logs/full/shard_%A_%a.out" --error="$ROOT/runtime/logs/full/shard_%A_%a.err" "$ROOT/slurm/magiccube_full_shard.slurm")
sim=${sim%%;*}
matrix=$(sbatch --parsable --dependency="afterok:$sim" --export="$EXPORT" "$ROOT/slurm/magiccube_aggregate.slurm")
matrix=${matrix%%;*}
ppdf=$(sbatch --parsable --dependency="afterok:$matrix" --export="$EXPORT" "$ROOT/slurm/magiccube_full_ppdf.slurm")
ppdf=${ppdf%%;*}
plots=$(sbatch --parsable --dependency="afterok:$ppdf:$matrix" --export="$EXPORT" "$ROOT/slurm/magiccube_full_plot.slurm")
plots=${plots%%;*}
heatmaps=$(sbatch --parsable --array="0-$((P-1))%$PLOT_CAP" --dependency="afterok:$ppdf" --export="$EXPORT" "$ROOT/slurm/magiccube_heatmap.slurm")
heatmaps=${heatmaps%%;*}
validate=$(sbatch --parsable --dependency="afterok:$plots:$heatmaps" --export="$EXPORT" --output="$ROOT/runtime/logs/full/validate_%j.out" --error="$ROOT/runtime/logs/full/validate_%j.err" "$ROOT/slurm/magiccube_validate.slurm")
validate=${validate%%;*}
printf 'tasks=%s worker_shards=%s worker_walltime=%s heatmap_tasks=%s heatmap_concurrency=%s\nshards=%s matrix=%s ppdf=%s plots=%s heatmaps=%s validate=%s\n' "$N" "$SHARDS" "$WORKER_WALLTIME" "$P" "$PLOT_CAP" "$sim" "$matrix" "$ppdf" "$plots" "$heatmaps" "$validate"
