#!/bin/bash
#SBATCH --job-name=onecube_img_stage
#SBATCH --output="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCubeImagingFinal/runtime/logs/stage_%A_%a.out"
#SBATCH --error="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCubeImagingFinal/runtime/logs/stage_%A_%a.err"
#SBATCH --partition=general-compute
#SBATCH --qos=general-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=04:00:00

set -euo pipefail

PROJECT_ROOT="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCubeImagingFinal"
PYTHON="/user/kmparmar/venv/bin/python"
cd "$PROJECT_ROOT"
stage="${1:-}"

case "$stage" in
    reduce_calibration) script="scripts/reduce_calibration.py" ;;
    analyze_system) script="scripts/assemble_analyze.py" ;;
    reconstruct) script="scripts/phantom_reconstruct.py" ;;
    validate_runtime) script="scripts/validate_imaging_pipeline.py"; set -- "$@" --stage runtime ;;
    finalize_report) script="scripts/finalize_report.py" ;;
    *)
        echo "Unknown imaging stage: $stage" >&2
        exit 2
        ;;
esac

env -u PYTHONPATH "$PYTHON" "$script" "${@:2}"
