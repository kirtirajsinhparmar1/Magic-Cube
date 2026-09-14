# Magic-Cube Step 4 Manual Runtime Runbook

## 1. Purpose

This runbook executes one corrected bounded Step-4 geometry, sensitive-detector, ROOT-schema, and runtime-identity rerun. The second real run, Slurm job 25779058, retained the earlier sensitive-detector and Tree-output fixes but exposed GATE's default centered `cubicArray` placement. The generator now explicitly preserves each frozen family translation as its first-copy center. Codex prepared this correction without running GATE, contacting Slurm, submitting a job, executing probes, or executing the external smoke test.

## 2. Prerequisites

Use a normal UB CCR shell where the following scheduler query works for you:

    sinfo -M ub-hpc

The submitted job uses the user-confirmed ub-hpc cluster, general-compute partition, and general-compute QOS.

## 3. Working Directory

Change to the exact repository directory. Keep the quotation marks because the path contains a space:

    cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"

## 4. Optional Scheduler Check

If desired, make one scheduler health check from the normal CCR shell:

    sinfo -M ub-hpc

This is a user-side check. It was not run by Codex.

## 5. Static Preparation Check

Run the pure static Step-4 preparation validator:

    python validate_magiccube_step4_preparation.py

It should print:

    Magic-Cube Step-4 preparation validation: PASS

This check now also requires explicit no-autocenter semantics for all eight
generated cubic arrays.

The frozen Step-3 geometry validator is also safe and appropriate before submission:

    python validate_magiccube_geometry.py

Do not run run_magiccube_step4_runtime.py directly on the login node.

## 6. Submit Step 4

Submit one corrected asynchronous, non-array job:

    sbatch magiccube_step4_job.sh

The expected response is:

    Submitted batch job <NEW_JOB_ID>

Record the returned new job ID.

## 7. Monitor Job

An optional single status check is:

    squeue -j <NEW_JOB_ID>

Repeated polling is not required. Replace <NEW_JOB_ID> with the numeric ID returned at submission.

## 8. Inspect Slurm Result

The audited relative SBATCH log names are:

    magiccube_step4_<NEW_JOB_ID>.out
    magiccube_step4_<NEW_JOB_ID>.err

After the job leaves the queue, inspect them from the submission directory:

    sed -n '1,320p' "magiccube_step4_<NEW_JOB_ID>.out"
    sed -n '1,320p' "magiccube_step4_<NEW_JOB_ID>.err"

An empty stderr file is normal. A nonzero exit, traceback, GATE fatal error, or missing completion line requires review before any rerun.

## 9. Runtime Output Directory

The dedicated runtime directory is:

    /vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step4

After the job finishes, list the resulting artifacts without deleting the prior failure evidence:

    ls -lah "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step4"

Expected major artifacts include:

- environment.txt
- static_geometry_validation.stdout and static_geometry_validation.stderr
- geometry_check.stdout, geometry_check.stderr, and geometry_check.exit_code
- probe_manifest.json
- up to 32 probe macros, per-family hit ROOT files, stdout/stderr logs, and status JSON files
- one smoke_140kev macro, per-family hit ROOT files, stdout/stderr log, and status JSON file
- runtime_run_summary.json

Do not delete the failed-run evidence from jobs 25778972 or 25779058. The rerun may replace same-named generated artifacts, but each status JSON records only files changed by its current GATE invocation, and analysis rejects nonzero GATE exit status. The tiny ROOT files from the aborted probes are not valid results.

The ROOT inspector writes these evidence summaries in the working directory only after real runtime data exist:

- magiccube_runtime_id_observations.csv
- magiccube_runtime_identity.json

## 10. Expected Runtime Sequence

The job performs, in order:

1. module loading and environment capture;
2. frozen Step-3 static validation;
3. geometry-only GATE initialization with explicit first-copy/no-autocenter repeated families;
4. no-system sensitive attachment of only the four GAGG families;
5. probe_00, followed only on success by the remaining fixed 30-keV probes derived from detector_map.csv;
6. one external isotropic 140-keV smoke source at (0,0,-66) mm;
7. ROOT schema discovery and runtime identity analysis;
8. final Step-4 runtime validation.

The shell exits on a true stage failure, so later stages do not mask an earlier error.

## 11. What Success Looks Like

The Slurm stdout should end with the runtime PASS result and job completion line. The resulting evidence should establish:

- geometry initialization PASS;
- useful hits from all four sensitive GAGG families;
- current usable ROOT hit collections for all 32 probes and the one smoke run, each backed by GATE exit code 0;
- no observed K9-sensitive hits;
- detector identity classified as ID_ONLY_VALIDATED, ID_PLUS_FAMILY_VALIDATED, or POSITION_DERIVED_REQUIRED;
- external 140-keV smoke-test GAGG hits.

POSITION_DERIVED_REQUIRED is an acceptable Step-4 result when runtime hierarchy fields are ambiguous but hit positions map uniquely to detector_map.csv.

## 12. What Failure Looks Like

If the job fails, DO NOT automatically rerun it. Preserve and provide:

- magiccube_step4_<NEW_JOB_ID>.out;
- magiccube_step4_<NEW_JOB_ID>.err;
- the relevant geometry, probe, smoke, or analysis log;
- the status JSON files and list of files left in the runtime output directory.

Review those artifacts before changing statistics, macros, modules, or detector assumptions. A scheduler failure is different from a GATE/model failure and must not be interpreted as scientific evidence.

## 13. DO NOT PROCEED TO STEP 5

Step 5 begins only after the real Step-4 outputs have been reviewed and the detector-identity conclusion is accepted. Do not start a source grid, system matrix, reconstruction, sensitivity study, or paper-performance comparison from this runbook.
