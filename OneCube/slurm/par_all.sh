#!/bin/bash
# Submit the complete OneCube dependency graph. This script only submits jobs.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$BASH_SOURCE")" && pwd)"

sim_job=$(sbatch --parsable "$SCRIPT_DIR/onecube_sim.slurm")
merge_job=$(sbatch --parsable --dependency=afterok:"$sim_job" "$SCRIPT_DIR/onecube_merge.slurm")
ppdf_job=$(sbatch --parsable --dependency=afterok:"$merge_job" "$SCRIPT_DIR/onecube_ppdf.slurm")
sysmat_job=$(sbatch --parsable --dependency=afterok:"$merge_job" "$SCRIPT_DIR/onecube_sysmat.slurm")
plot_job=$(sbatch --parsable --dependency=afterok:"$ppdf_job":"$sysmat_job" "$SCRIPT_DIR/onecube_plot.slurm")
validation_job=$(sbatch --parsable --dependency=afterok:"$plot_job" "$SCRIPT_DIR/onecube_validate.slurm")

echo "simulation_job=$sim_job"
echo "merge_job=$merge_job"
echo "ppdf_job=$ppdf_job"
echo "system_matrix_job=$sysmat_job"
echo "plot_job=$plot_job"
echo "validation_job=$validation_job"
