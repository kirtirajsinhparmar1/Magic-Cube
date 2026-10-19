# Magic-Cube Step-7 Runbook

The prior attempt, job `26105689`, failed before acquisition because GATE 9.4
does not provide the `gps/rot1` namespace used by the pre-correction source.
The source uses `gps/pos/rot1`, `gps/pos/rot2`, `gps/ang/rot1`, and
`gps/ang/rot2`. The final bounded source-direction correction sets angular
`rot1 = (0,0,-1)` and retains angular `rot2 = (0,1,0)`, so the unchanged
central angular direction points +Z toward the detector. The angular limits
and all scientific source parameters are unchanged. Its current SHA-256 is
`48e39d03f081cc4b95a9d065566743890e23fda4e8fcfc649d7f70ca70ea9c31`.
Job `26109308` reached acquisition without a GATE error but produced no
events because the prior central direction pointed away; identity remains
`UNKNOWN UNTIL SUCCESSFUL STEP-7 RUNTIME` until the corrected run produces
ROOT events.

This runbook prepares one bounded Step-7 runtime.  The real production main
`magiccube_production_main.mac` remains unchanged at 15 s.  The job now runs
`magiccube_step7_bounded_main.mac`, which is identical except for a 1 s
acquisition stop and the isolated output macro
`magiccube_step7_bounded_output.mac`.  The bounded file is validation-only;
full production and the later parallel workflow must use the real 15 s main.
Codex does not execute the Gate or Slurm commands.

Job `26105745` is recorded as a successful acquisition-start / production-
scale timeout, not a GATE compatibility failure.  Its 15 s workload was
approximately 55.5 million primary decays.

## Preparation

From the working directory:

    cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"

Run the static preparation check:

    python validate_magiccube_step7_preparation.py

It must report `STATIC STEP-7 PREPARATION: PASS`.  A collision with an
existing `magiccube_production*.root` artifact blocks submission; do not
delete historical production evidence.

## One bounded runtime

After static preparation passes, submit exactly one job:

    sbatch magiccube_step7_end_to_end_job.sh

Then monitor it with:

    squeue -j <JOBID>

After completion, inspect the scheduler record and wrapper logs:

    sacct -j <JOBID> \
      --format=JobID,JobName,State,ExitCode,Elapsed,NodeList

    cat magiccube_step7_<JOBID>.out

    cat magiccube_step7_<JOBID>.err

    cat "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step7/gate_exit_code.txt"

    grep -E "Fatal Exception|COMMAND NOT FOUND|Failed to get the system corresponding to that digitizer|GateSpatialResolution|G4Exception|abort" \
      "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step7/gate.log"

Run the output/schema validator from the working directory:

    env -u PYTHONPATH /user/kmparmar/venv/bin/python \
      validate_magiccube_step7_outputs.py \
      --output-dir "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step7"

Read the generated schema evidence:

    cat "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step7/step7_root_schema.txt"

## Interpretation

`STEP7_END_TO_END_VALIDATED` requires Gate 0, nonzero Hits, nonzero Singles,
and successful position-derived canonical identity recovery.  A successful
GATE workflow with missing position branches is reported as
`STEP7_RUNTIME_VALID_IDENTITY_PENDING`; native volume IDs must not be treated
as canonical detector IDs.

Do not modify the frozen production macros or repair output identity in this
Step-7 task.  Any identity-output adaptation is a separate, bounded follow-up
after the schema evidence is reviewed.
