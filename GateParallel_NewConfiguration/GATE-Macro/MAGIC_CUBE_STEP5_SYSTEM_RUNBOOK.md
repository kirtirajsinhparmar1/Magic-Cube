# Magic-Cube Step-5 System Candidate Runbook

This runbook executes one bounded manual compatibility test for the centered
`cylindricalPET` wrapper candidate. It does not run a production source or
measure detector performance.

## 1. Candidate Under Test

The test uses:

```text
magiccube_production_geometry.mac
magiccube_production_system.mac
magiccube_production_physics.mac
magiccube_production_digitizer.mac
magiccube_step5_system_check.mac
```

The production geometry is:

```text
world -> cylindricalPET -> panel -> module -> block -> magicCubeMother
```

All wrappers are centered and Air-only. The detector body is unchanged from
the frozen Magic-Cube geometry. The production system maps
`rsector->panel`, `module->module`, `submodule->block`, and
`crystal->magicCubeMother`, then attaches ordinary CrystalSD to the four
GAGG families only.

The previous job `26037645` failed with exit 255 at system-macro parsing
because `/gate/systems/cylindricalPET/rsector/attach magicCubeMother` had no
corresponding physical hierarchy. This candidate specifically tests that
missing hierarchy and has not been runtime validated yet.

## 2. Static Preparation

From the user's normal CCR shell:

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
python validate_magiccube_step5_system_preparation.py
```

Proceed only if the validator prints `STATIC PREPARATION: PASS`.

## 3. Submit One Bounded Job

Submit the single non-array job:

```bash
sbatch magiccube_step5_system_job.sh
```

The job script uses the explicit working directory and CCR module setup. It
keeps Slurm output names local (`magiccube_step5_system_%j.out` and
`magiccube_step5_system_%j.err`) so the space in `Magic Cube` is not parsed
inside an `#SBATCH` path.

## 4. Monitor and Inspect

Replace `<JOBID>` with the ID returned by `sbatch`:

```bash
squeue -j <JOBID>
sacct -j <JOBID> --format=JobID,JobName,State,ExitCode,Elapsed,NodeList
cat magiccube_step5_system_<JOBID>.out
cat magiccube_step5_system_<JOBID>.err
cat "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_system/gate_exit_code.txt"
```

Inspect the Gate log for the bounded failure conditions:

```bash
grep -E "COMMAND NOT FOUND|Fatal Exception|G4Exception|Failed to get the system corresponding to that digitizer|abort" "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_system/magiccube_step5_system_gate.log"
```

The key question is whether the real wrapper hierarchy makes all four system
attachments parse and allows initialization and `SpatialResolution` to run.

## 5. Validate Outputs

Run the output validator with the actual Gate exit code recorded in
`gate_exit_code.txt`:

```bash
python validate_magiccube_step5_system_outputs.py --output-dir "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_system" --gate-exit-code <ACTUAL_GATE_EXIT_CODE>
```

The bounded PASS requirements are Gate exit code 0, no fatal/system lookup
exception, readable non-empty Hits and Singles when the ROOT Python
environment permits content inspection, and no digitizer abort. A NumPy or
uproot import failure is reported separately as a validator-environment
issue; it is not treated as a Gate failure.

## 6. Scope Boundary

Do not inspect sensitivity, spectra, spatial-FWHM performance, PPDF,
system-matrix output, or reconstruction in this test. Do not modify the
frozen Step-4 system, detector map, physics, or digitizer files.
