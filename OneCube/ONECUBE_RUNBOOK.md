# OneCube manual runbook

The commands below are for the user to run on the UB CCR environment. Codex
does not execute Gate, Slurm submission, ROOT merging, or runtime jobs.

## A — Static preparation check

~~~
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube"

env -u PYTHONPATH /user/kmparmar/venv/bin/python \
    scripts/validate_preparation.py
~~~

The expected result is:

~~~
ONECUBE STATIC PREPARATION: PASS
~~~

## B — Recommended complete pipeline

~~~
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube/slurm"

bash par_all.sh
~~~

par_all.sh prints the six submitted job IDs and only creates afterok
dependencies.

## C — Monitoring

~~~
squeue -u kmparmar
~~~

For a completed job:

~~~
sacct -j <JOB_ID> \
    --format=JobID,JobName,State,ExitCode,Elapsed,NodeList
~~~

Inspect the Gate log after the simulation job completes:

~~~
sed -n '1,240p' \
    "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube/runtime/logs/gate.log"
~~~

## D — Manual individual-stage submission

From the OneCube/slurm directory, submit stages manually when debugging a
dependency:

~~~
SIM_JOB=$(sbatch --parsable onecube_sim.slurm)
MERGE_JOB=$(sbatch --parsable --dependency=afterok:$SIM_JOB onecube_merge.slurm)
PPDF_JOB=$(sbatch --parsable --dependency=afterok:$MERGE_JOB onecube_ppdf.slurm)
SYSMAT_JOB=$(sbatch --parsable --dependency=afterok:$MERGE_JOB onecube_sysmat.slurm)
PLOT_JOB=$(sbatch --parsable \
    --dependency=afterok:$PPDF_JOB:$SYSMAT_JOB onecube_plot.slurm)
VALIDATE_JOB=$(sbatch --parsable \
    --dependency=afterok:$PLOT_JOB onecube_validate.slurm)
echo "$SIM_JOB $MERGE_JOB $PPDF_JOB $SYSMAT_JOB $PLOT_JOB $VALIDATE_JOB"
~~~

If only a downstream stage needs to be rerun after its inputs are already
valid, submit that worker directly, for example:

~~~
sbatch onecube_ppdf.slurm
sbatch onecube_sysmat.slurm
~~~

Do not run a downstream stage after a failed prerequisite without first
correcting the failed product.

## E — Final outputs

~~~
results/validation/final_validation.json
results/ppdf/ppdf.parquet
results/system_matrix/system_matrix.parquet
results/system_matrix/system_matrix.npy
results/plots/system_matrix_heatmap.png
results/plots/onecube_response_summary.png
~~~

The .npy matrix stores response_per_Bq_s; the metadata JSON documents the
quantity and units.

## F — Final success text

The authoritative validator must print:

~~~
ONECUBE_END_TO_END_PASS
~~~

That result proves the complete one-element software/data architecture only.
It does not validate the future full Magic-Cube science configuration.
