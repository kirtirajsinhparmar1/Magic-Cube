# Magic-Cube Step-5 Digitizer Runtime Runbook

Run the following commands manually from the normal UB CCR shell. Codex does
not execute the runtime job.

## 1. Static preparation

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
python validate_magiccube_step5_digitizer_runtime_preparation.py
```

Expected result:

```text
STATIC DIGITIZER-RUNTIME PREPARATION: PASS
```

## 2. Submit the one bounded job

```bash
sbatch magiccube_step5_digitizer_runtime_job.sh
squeue -j <JOBID>
```

## 3. Inspect completion

```bash
sacct -j <JOBID> \
  --format=JobID,JobName,State,ExitCode,Elapsed,NodeList

cat magiccube_step5_digitizer_<JOBID>.out
cat magiccube_step5_digitizer_<JOBID>.err
```

The bounded runtime artifacts are under:

```text
/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_digitizer
```

Inspect the Gate status and relevant errors:

```bash
cat "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_digitizer/gate_exit_code.txt"
grep -E "Failed to get the system corresponding|GateSpatialResolution|Fatal Exception|COMMAND NOT FOUND|abort" \
  "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_digitizer/gate.log" || true
```

## 4. Validate Hits and Singles

```bash
env -u PYTHONPATH /user/kmparmar/venv/bin/python \
  validate_magiccube_step5_digitizer_runtime_outputs.py \
  --output-dir "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_digitizer"
```

The validator discovers all readable per-family Hits and Singles ROOT files.
If uproot/NumPy cannot load, it reports
`VALIDATION_INCOMPLETE_ENVIRONMENT_ERROR` separately from Gate status.

Do not change the production digitizer or system based on partial output. Use
the reported classification to determine the next bounded task.
