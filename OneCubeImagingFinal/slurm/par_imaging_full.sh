#!/usr/bin/env bash
# Single manual entry point for the complete OneCube imaging production graph.
set -euo pipefail

PROJECT_ROOT="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCubeImagingFinal"
PYTHON="/user/kmparmar/venv/bin/python"
SLURM_DIR="$PROJECT_ROOT/slurm"
cd "$PROJECT_ROOT"

SLURM_WORKERS=(
    "$SLURM_DIR/imaging_gate_array.slurm"
    "$SLURM_DIR/imaging_stage.slurm"
)
for worker_script in "${SLURM_WORKERS[@]}"; do
    if [[ ! -f "$worker_script" || ! -r "$worker_script" ]]; then
        echo "Preflight failed: required Slurm worker is missing or unreadable: $worker_script" >&2
        exit 2
    fi
done

if ! command -v sbatch >/dev/null 2>&1; then
    echo "Preflight failed: sbatch is not available in this environment." >&2
    exit 127
fi

mkdir -p runtime/logs
env -u PYTHONPATH "$PYTHON" scripts/prepare_experiment.py --json
env -u PYTHONPATH "$PYTHON" scripts/validate_imaging_pipeline.py --stage prepare

worker_count="$(env -u PYTHONPATH "$PYTHON" -c 'import json; print(json.load(open("config/imaging_config.json"))["resources"]["gate_workers"])')"
array_spec="0-$((worker_count - 1))%$worker_count"

calibration_id="$(sbatch --parsable \
    --array="$array_spec" \
    --export="ALL,IMAGING_STAGE=calibration,IMAGING_SHARD_COUNT=$worker_count" \
    "$SLURM_DIR/imaging_gate_array.slurm")"
reduction_id="$(sbatch --parsable \
    --dependency="afterok:$calibration_id" \
    "$SLURM_DIR/imaging_stage.slurm" reduce_calibration)"
analysis_id="$(sbatch --parsable \
    --dependency="afterok:$reduction_id" \
    "$SLURM_DIR/imaging_stage.slurm" analyze_system)"
phantom_id="$(sbatch --parsable \
    --array="$array_spec" \
    --dependency="afterok:$analysis_id" \
    --export="ALL,IMAGING_STAGE=phantom,IMAGING_SHARD_COUNT=$worker_count" \
    "$SLURM_DIR/imaging_gate_array.slurm")"
reconstruction_id="$(sbatch --parsable \
    --dependency="afterok:$phantom_id" \
    "$SLURM_DIR/imaging_stage.slurm" reconstruct)"
validation_id="$(sbatch --parsable \
    --dependency="afterok:$reconstruction_id" \
    "$SLURM_DIR/imaging_stage.slurm" validate_runtime)"
report_id="$(sbatch --parsable \
    --dependency="afterok:$validation_id" \
    "$SLURM_DIR/imaging_stage.slurm" finalize_report)"

cat <<EOF
Submitted complete OneCube imaging workflow:
  calibration array: $calibration_id
  calibration reduction: $reduction_id
  system matrix and characterization: $analysis_id
  independent Gate phantom array: $phantom_id
  MLEM and quantitative evaluation: $reconstruction_id
  runtime validation: $validation_id
  final report update: $report_id
Maximum Gate concurrency: $worker_count array workers
EOF
