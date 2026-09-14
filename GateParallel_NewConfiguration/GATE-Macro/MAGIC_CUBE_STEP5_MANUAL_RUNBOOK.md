# Magic-Cube Step 5 Manual Runbook

This runbook is for the user’s UB CCR terminal. The commands below are not
executed by Codex. The harness is bounded and diagnostic-only; it is not a
production source/output/main-macro implementation.

## 1. Review the prepared files

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
/user/kmparmar/venv/bin/python validate_magiccube_step5_preparation.py
```

The preparation validator must report `STATIC PREPARATION: PASS`.

## 2. Submit the bounded runtime check manually

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
sbatch magiccube_step5_digitizer_job.sh
```

The job wrapper loads the same UB CCR environment recorded by the successful
Step-4 run:

```text
gcc/11.2.0
geant4/11.2.1
geant4-data/11.2
openmpi/4.1.1
gate/9.4
```

The wrapper then runs only:

```text
Gate magiccube_step5_digitizer_check.mac
```

and invokes the output validator with the resulting exit code.

## 3. Validate or inspect the result

The job writes into:

```text
/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5
```

The expected harness ROOT file is:

```text
magiccube_step5_digitizer.root
```

The job also writes the Gate log and exit-code record. If a separate manual
validation invocation is needed after the job, run:

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
/user/kmparmar/venv/bin/python validate_magiccube_step5_outputs.py \
  --output-dir "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5"
```

For a runtime pass, the validator must report:

- Gate exit code `0`;
- readable ROOT output;
- at least one non-empty Hits output;
- at least one non-empty Singles output;
- no fatal geometry or digitizer exception.

The common original `Singles` collection name is expected. Explicit family
names are reported if present, but the harness does not invent separate
collection names because that would change the original output convention.

## 4. Failure handling

If the runtime check fails, inspect:

```bash
sed -n '1,240p' "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5/magiccube_step5_digitizer_gate.log"
```

Do not alter the frozen geometry, detector map, lattice map, or Step-4
no-system attachment while diagnosing this bounded check. A failure of the
digitizer/no-system compatibility check should be recorded as the exact GATE
error and resolved in a later scoped decision; it should not trigger a new
detector-response architecture in this step.

## 5. Scope boundary

This runbook does not run or prepare production source variation, production
output naming, parallel arrays, ROOT merging, PPDF generation, system-matrix
generation, normalization, plotting, or reconstruction.
