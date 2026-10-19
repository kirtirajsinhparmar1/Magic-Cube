# Magic-Cube Step-5 Raw-Hits Diagnostic Runbook

Run these commands manually from the normal UB CCR shell. They are not
executed by Codex.

## 1. Static preparation

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
python validate_magiccube_step5_hits_preparation.py
```

Expected result:

```text
STATIC HITS-DIAGNOSTIC PREPARATION: PASS
```

## 2. Submit the one bounded job

```bash
sbatch magiccube_step5_hits_job.sh
```

Record the returned job ID, then monitor it:

```bash
squeue -j <JOBID>
```

## 3. Inspect completion

```bash
sacct -j <JOBID> \
  --format=JobID,JobName,State,ExitCode,Elapsed,NodeList

cat magiccube_step5_hits_<JOBID>.out
cat magiccube_step5_hits_<JOBID>.err
```

The job writes its bounded artifacts under:

```text
/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_hits
```

Inspect the two independent Gate exit codes and logs:

```bash
cat "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_hits/internal_gate_exit_code.txt"
cat "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_hits/external_gate_exit_code.txt"

grep -E "COMMAND NOT FOUND|Fatal Exception|G4Exception|Failed to get the system corresponding" \
  "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_hits/internal_gate.log" || true

grep -E "COMMAND NOT FOUND|Fatal Exception|G4Exception|Failed to get the system corresponding" \
  "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_hits/external_gate.log" || true
```

## 4. Validate raw Hits

```bash
env -u PYTHONPATH /user/kmparmar/venv/bin/python \
  validate_magiccube_step5_hits_outputs.py \
  --output-dir "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_hits"
```

The validator reports Test A and Test B separately and emits one final
interpretation. If the Python environment cannot import uproot/NumPy, it
reports `VALIDATION_INCOMPLETE_ENVIRONMENT_ERROR`; the Gate exit codes and
logs remain the authoritative runtime evidence.

Do not re-enable the digitizer or change the production system as part of this
diagnostic. The next decision depends only on the internal/external Hits
result.
