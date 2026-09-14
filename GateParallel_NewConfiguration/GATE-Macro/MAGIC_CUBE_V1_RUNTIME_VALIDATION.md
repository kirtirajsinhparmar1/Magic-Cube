# Magic-Cube V1 GATE Runtime Validation

## 1. Purpose

Step 4 is the controlled transition from the Step-3 static geometry proof to GATE runtime validation. It is limited to geometry initialization, sensitive GAGG attachment, ROOT-hit schema inspection, and canonical detector-identity validation. It is not a production simulation or a paper-performance study.

## 2. Inherited Frozen Contracts

Steps 1–3 remain unchanged: the Air `magicCubeMother` is 67.2 x 67.2 x 32.0 mm; the conceptual lattice is 16 x 16 x 16; material cells are 2 mm cubes at 4.2 mm lateral pitch; and `(ix + iy + k) % 2 == 0` selects GAGG. The four GAGG families are `mc_gagg_ee`, `mc_gagg_eo`, `mc_gagg_oe`, and `mc_gagg_oo`; the four K9 families remain passive and use `K9_V1_PROXY`.

Canonical detector IDs remain `detector_id = d * 256 + iy * 16 + ix`. Runtime IDs were not assumed to equal this formula.

## 3. Runtime Environment

The exact legacy module stack from `par_vscratch.sh` loaded successfully during pre-flight:

- `gcc/11.2.0`
- `geant4/11.2.1`
- `geant4-data/11.2`
- `openmpi/4.1.1`
- `gate/9.4`

`Gate` resolved to `/cvmfs/soft.ccr.buffalo.edu/versions/2023.01/easybuild/software/avx512/MPI/gcc/11.2.0/openmpi/4.1.1/gate/9.4/bin/Gate`. The authoritative compute-node banner from Slurm job 25778972 reported GATE 9.4 (2024) with Geant4 11.2.1. The earlier Gate 9.2 uncertainty is superseded by this real runtime evidence.

The venv at `/user/kmparmar/venv/bin/python` imports `uproot 5.7.3` when the module-provided `PYTHONPATH` is unset. The Step-4 job harness therefore uses `env -u PYTHONPATH` for uproot commands.

The user manually submitted Slurm job 25778972 from a normal CCR shell, and the job reached compute-node GATE execution. The earlier scheduler-access problem was specific to the Codex execution environment and is not a Magic-Cube project blocker.

## 4. Geometry Initialization

The geometry-only stage loads `GateMaterials.db`, defines a 200 mm Air world, executes `magiccube_geometry.mac`, and initializes GATE.

In Slurm job 25778972, `geometry_check.exit_code` recorded 0. The dedicated stdout shows GATE geometry, physics, and actor initialization completing normally; its stderr contains only the non-fatal `Materials.xml` warnings. The isolated geometry initialization stage therefore **PASSed**.

## 5. Runtime Overlap Assessment

No explicit runtime overlap command was run. Geometry initialization completed without a fatal geometry error, while Step 3 remains the only explicit non-overlap validation. This is not yet a dedicated runtime overlap pass.

## 6. Sensitive Detector Attachment

The first probe used system-dependent `attachCrystalSD` on the four `mc_gagg_*` families. GATE rejected each request because the volumes do not belong to a scanner system, so no valid hit output could result from that attempt.

The installed GATE 9.4 binary contains `attachCrystalSDnoSystem`. The Step-4 macro has been corrected to use that command for exactly the four GAGG families; K9, Air, and the mother remain passive. This correction is prepared but remains runtime-unvalidated until the user reruns the job.

## 7. Diagnostic Probe Design

The harness deterministically selects eight coordinates `(rx, ry, rz)` per GAGG family: `(0,0,0)`, `(1,0,0)`, `(0,1,0)`, `(0,0,1)`, `(7,0,0)`, `(0,7,0)`, `(0,0,7)`, and `(7,7,7)`. It reads their canonical locations from `detector_map.csv`, for 32 probes total.

`probe_00` was launched, but it aborted before event acquisition completed. The remaining probes were not attempted because the runner failed fast.

## 8. Diagnostic Source

The prepared probe macros use a 30 keV point GPS source at each selected GAGG center with 100 Bq for one second. This is an identity diagnostic only, not a Magic-Cube physics model. The prepared external smoke macro uses a 140 keV point GPS source at `(0, 0, -66)` mm with 20,000 Bq for one second.

The `probe_00` source configuration was parsed, but GATE aborted on the later invalid Tree command before `startDAQ`. No diagnostic events or smoke-test events completed.

## 9. ROOT Output Schema

The failed probe left four approximately 479-byte files named for the GAGG hit collections. They were produced after sensitive attachment failed and before a fatal macro abort, so they are invalid/incomplete artifacts and have no scientific interpretation. The inspector now requires GATE exit code 0, an expected readable hit collection/tree, and usable hit data rather than accepting file existence.

## 10. Runtime volumeID / Hierarchy Behavior

No runtime volume or hierarchy fields were observed. No interpretation of GATE copy ordering was made.

## 11. Canonical Mapping Result

**UNRESOLVED.** No GATE hits were available to establish either an ID-only, ID-plus-family, or position-derived mapping.

## 12. Position-Based Mapping Validation

The prepared inspector maps a hit only when exactly one `detector_map.csv` GAGG cube contains its position within the 1 mm half-size plus a `1e-6 mm` numerical tolerance. This algorithm was not executed because no valid hits exist.

## 13. 140-keV External Smoke Test

The required smoke test at `(0, 0, -66)` mm was not executed. Its hit count, unique canonical detectors, depth distribution, and family counts are unknown.

## 14. What Step 4 Proves

Job 25778972 proves manual Slurm submission, compute-node execution, GATE 9.4 and Geant4 11.2.1 startup, material recognition sufficient for initialization, parsing of the eight-family geometry, diagnostic PhotoElectric registration, and isolated geometry initialization.

It does not prove successful no-system sensitive attachment, usable ROOT hits, detector identity, the external smoke response, or overall Step-4 completion.

## 15. What Step 4 Does NOT Prove

The first real run does not prove dedicated runtime overlap status, successful sensitive-detector behavior, usable ROOT output, canonical identity mapping, external-source response, final gamma physics, K9 attenuation accuracy, Compton/Rayleigh modeling, energy resolution, an energy window, multi-crystal handling, sensitivity, a system matrix, resolution, MLEM, or paper-level matching.

## 16. Step-5 Handoff

Step 5 must not begin. The user must manually submit one corrected bounded Step-4 rerun from a normal CCR shell, then the resulting logs and ROOT evidence must be reviewed before any Step-5 work. No frozen scientific contract should change during that execution.

## 17. Runtime Identity Contract

| Runtime field or method | Meaning | Validation status | Future use |
| --- | --- | --- | --- |
| GATE volumeID / hierarchy fields | GATE runtime placement identity | No valid hit schema observed | Inspect across fixed probes after corrected rerun |
| GAGG hit position | Physical interaction location | No valid hit data observed | Map uniquely to `detector_map.csv` if hierarchy IDs are ambiguous |
| Canonical `detector_id` | Frozen software contract, 0..2047 | Static-only | Must remain independent of arbitrary GATE copy ordering |

## First Real Runtime Attempt — Slurm Job 25778972

Current status: **RUNTIME_CORRECTION_REQUIRED**.

- Slurm submission: PASS.
- Compute-node execution: PASS.
- GATE launch: PASS.
- Runtime versions: GATE 9.4 (2024), Geant4 11.2.1.
- Dedicated geometry initialization: PASS (`geometry_check.exit_code` = 0).
- Probe 00: FAIL (`exit_code` = 255).
- Cause 1: system-dependent CrystalSD attachment was rejected for all four GAGG families because they belong to no scanner system.
- Cause 2: `/gate/output/tree/singles/disable` was not a valid command and caused the fatal macro abort.
- `Materials.xml` warnings: informational and non-blocking because Step 4 transports no optical photons.
- Four approximately 479-byte ROOT files: invalid/incomplete failed-run artifacts; they must not be interpreted scientifically.

The correction uses locally verified `attachCrystalSDnoSystem`, removes the invalid Singles-disable command, and makes successful GATE status plus usable ROOT content prerequisites for analysis. Those corrections were exercised in job 25779058; that run exposed the separate repeater-encoding failure documented below.

## Second Real Runtime Attempt — Slurm Job 25779058

Current status: **RUNTIME_CORRECTION_REQUIRED**.

- Step-4 preparation validator before submission: PASS.
- Step-3 static geometry validator before submission: PASS.
- Slurm submission and compute-node execution: PASS.
- GATE launch: PASS.
- Runtime versions: GATE 9.4, Geant4 11.2.1.
- Dedicated geometry initialization: PASS (`geometry_check.exit_code` = 0).
- Probe 00: FAIL (`exit_code` = -6, abort signal).
- Fatal exception: `G4Exception` code `GeomMgt0002` from `G4SmartVoxelHeader::BuildNodes()`.
- Reported geometry failure: daughter `mc_gagg_ee_phys` was entirely outside mother `magicCubeMother_log`.

Local inspection of the installed GATE 9.4 implementation confirmed that a
new `cubicArray` defaults to `autoCenter = true`. With that default, the
family seed translations were treated as repeated-array centers even though
the frozen generator contract defines them as first-copy centers. The missing
explicit no-autocenter semantics therefore caused copies to be placed outside
the frozen mother. The generator now emits
`/gate/<family>/cubicArray/autoCenter false` for every family; this is a GATE
encoding correction and does not alter any scientific coordinate.

The preceding corrections remained accepted in this run:
`attachCrystalSDnoSystem` did not produce the former system-membership
attachment failure, and the invalid `/gate/output/tree/singles/disable`
command remained absent. The `Materials.xml` warning remains informational
and non-blocking because Step 4 transports no optical photons. The
approximately 254-byte ROOT files created by the aborted probe are incomplete
failed-run artifacts and are not scientific results. A new user-executed run
is required before Step 4 can pass.

## Historical Codex-Side Scheduler Evidence

The preferred synchronous request failed before submission with:

```text
sbatch: error: Batch job submission failed: Unable to contact slurm controller (connect failure)
```

The one permitted synchronous `srun` fallback also failed before the job script started:

```text
srun: error: Unable to confirm allocation for job 25688300: Unable to contact slurm controller (connect failure)
srun: Check SLURM_JOB_ID environment variable. Expired or invalid job 25688300
```

No Slurm job was submitted, allocated, or run by that Codex-side attempt; no GATE simulation was executed. This historical `BLOCKED_BY_SLURM` evidence reflects only the Codex execution environment. It was superseded as a scheduler finding by user-submitted job 25778972, while remaining preserved here for provenance.
