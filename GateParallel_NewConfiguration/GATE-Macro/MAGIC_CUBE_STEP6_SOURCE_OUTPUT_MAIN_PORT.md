# Magic-Cube Step-6 Source / Output / Main-Macro Port

## 1. Step-6 Objective

Step 6 prepares a faithful Magic-Cube port of the active local repository
source configuration, output configuration, and main GATE orchestration. The
local checkout is authoritative; the source files used were `SPEBT.mac`,
`source.mac`, `output.mac`, and `geometry.mac` in this working directory.

No production runtime, Slurm job, parallel workflow, PPDF, system matrix, or
reconstruction work is performed here.

## 2. Frozen Step-5 Foundation

Step 5 is closed with `STEP 5 CLOSED: PASS` in
`MAGIC_CUBE_STEP5_CLOSURE_AUDIT.md`. Its production geometry, system,
physics, digitizer, and detector-identity contract are treated as immutable
inputs. The Step-6 validator checks the SHA-256 values recorded by that
closure report before accepting this preparation.

## 3. Original Active Source

The active `source.mac` configures one GPS source:

- particle: `gamma`
- energy type: `Mono`
- monoenergy: `140.0 keV`
- activity: `0.0001 Ci`
- type: `Plane`
- shape: `Rectangle`
- centre: `-187.5 0. 0. mm`
- half sizes: `halfx 250 mm`, `halfy 250 mm`
- angular type: `iso`
- theta range: `90 deg` to `90 deg`
- phi range: `150 deg` to `210 deg`

The active `SPEBT.mac` sets the random engine to `MersenneTwister`, sets the
acquisition time from `0. s` to `15 s`, executes the source after
initialization and digitizer setup, and does not set an explicit seed.

## 4. Original Source Geometry Interpretation

The original `geometry.mac` places the detector panel at positive x:
`/gate/cylindricalPET/panel/placement/setTranslation 137 0 0 mm`. The active
source plane is at negative x, centred at `(-187.5, 0, 0) mm`. Thus the
original source/detector placement axis is x. The original source commands,
including their angular values, are preserved rather than scientifically
retuned.

## 5. Magic-Cube Source Orientation Adaptation

The frozen Magic-Cube convention places the source on the negative-z side of
the detector, with the detector depth along z. The bounded rigid coordinate
mapping used in `magiccube_production_source.mac` is:

```text
(x_orig, y_orig, z_orig) -> (-z_magic, y_magic, x_magic)
```

This maps the original source centre to `(0, 0, -187.5) mm` and maps the
original source-plane frame to `rot1 = (0, 0, 1)` and `rot2 = (0, 1, 0)`.
In GATE 9.4, the positional frame is expressed with
`/gate/source/source1/gps/pos/rot1` and `/gate/source/source1/gps/pos/rot2`.
The positional and angular GPS frames are configured separately. The
positional frame uses `/gate/source/source1/gps/pos/rot1 = (0,0,1)` and
`/gate/source/source1/gps/pos/rot2 = (0,1,0)`. The corrected angular frame
uses `/gate/source/source1/gps/ang/rot1 = (0,0,-1)` and
`/gate/source/source1/gps/ang/rot2 = (0,1,0)`, so the unchanged central
`theta = 90 deg`, `phi = 180 deg` direction points +Z toward Magic-Cube.
The source plane size, activity, energy, angular type, and angular ranges are
not changed. Step 7 must provide the first runtime check of transport under
the Magic-Cube orientation.

PRESERVED values: particle, energy, activity, plane shape and size, angular
type and ranges, acquisition duration, RNG engine, and absent explicit seed.

GEOMETRY-FORCED changes: source centre and source-plane orientation only.

The final bounded source-direction correction follows Step-7 job `26109308`,
which completed with Gate exit 0 and no GATE errors but produced zero Hits and
zero Singles because its central direction was -Z, away from Magic-Cube. Only
the angular `rot1` sign changed from `(0,0,+1)` to `(0,0,-1)`; this is a
GATE-syntax and coordinate-frame compatibility correction, not a scientific
source redesign.

### Bounded source-frame compatibility correction

Step-7 job `26105689` reached production source parsing but failed with Gate
exit `255` because GATE 9.4 reported:

```text
COMMAND NOT FOUND /gate/source/source1/gps/rot1 0. 0. 1.
```

The correction is a **GATE-SYNTAX + COORDINATE-FRAME COMPATIBILITY
CORRECTION**, not a scientific source redesign:

- `gps/rot1` -> `gps/pos/rot1`;
- `gps/rot2` -> `gps/pos/rot2`;
- add `gps/ang/rot1` and `gps/ang/rot2` with the same frame vectors.

Theta and phi limits remain numerically unchanged. Acquisition did not begin
in job `26105689`, so that run produced no detector-output or identity
evidence. The corrected source requires a new bounded Step-7 runtime.

## 6. Source Parameters Preserved

| Parameter | Original | Magic-Cube | Status |
|---|---|---|---|
| Particle | gamma | gamma | Preserved |
| Energy | 140.0 keV mono | 140.0 keV mono | Preserved |
| Activity | 0.0001 Ci | 0.0001 Ci | Preserved |
| Source type | Plane | Plane | Preserved |
| Source shape | Rectangle | Rectangle | Preserved |
| Centre | (-187.5, 0, 0) mm | (0, 0, -187.5) mm | Coordinate transform only |
| Half sizes | 250 mm, 250 mm | 250 mm, 250 mm | Preserved |
| Angular distribution | iso | iso | Preserved |
| Theta | 90–90 deg | 90–90 deg | Preserved |
| Phi | 150–210 deg | 150–210 deg | Preserved |
| Acquisition | 0–15 s | 0–15 s | Preserved |
| RNG | MersenneTwister | MersenneTwister | Preserved |
| Explicit seed | none | none | Preserved |

## 7. Original Active Output

The active `output.mac` enables the ROOT Tree backend, enables Tree Hits, and
requests the `Singles` collection. Its active filename is the original
parallel-workflow path containing `${SLURM_ARRAY_TASK_ID}`. Other output
commands in that file are commented out and are not ported.

## 8. Magic-Cube Output Port

`magiccube_production_output.mac` preserves the active ROOT Tree and Hits
mechanism and requests the four frozen production digitizer collections:

- `Singles_mc_gagg_ee`
- `Singles_mc_gagg_eo`
- `Singles_mc_gagg_oe`
- `Singles_mc_gagg_oo`

The output filename is the non-diagnostic production prefix
`./magiccube_production.root`. This is a path/naming adaptation; no custom
detector-ID branch, actor, ntuple, PPDF, or matrix output is added.

## 9. Detector Identity Implications

The canonical identity remains `POSITION_DERIVED_REQUIRED`, with

```text
detector_id = d*256 + iy*16 + ix
```

and `detector_map.csv` as the authoritative mapping. No Step-6 file changes
that contract. The static output classification is
`IDENTITY_OUTPUT_UNKNOWN_UNTIL_RUNTIME`: the faithful output commands do not
statically guarantee which position branches will be present in the final
ROOT files. Step 7 must inspect the actual ROOT schema and attempt the
position-derived recovery. No native GATE volume ID is treated as canonical.

## 10. Original Main-Macro Order

The active `SPEBT.mac` order is:

1. set `GateMaterials.db`;
2. execute `geometry.mac`;
3. execute `plate.mac`;
4. execute `system.mac`;
5. execute `physics.mac`;
6. `/gate/run/initialize`;
7. execute `digitizer.mac`;
8. execute `source.mac`;
9. set `MersenneTwister`;
10. set acquisition start and stop times;
11. execute `verbose.mac`;
12. execute `output.mac`;
13. `/gate/application/startDAQ`.

## 11. Magic-Cube Main-Macro Order

`magiccube_production_main.mac` preserves the same active order while
replacing the frozen detector-specific stages:

```text
GateMaterials.db
  -> magiccube_production_geometry.mac
  -> magiccube_production_system.mac
  -> magiccube_production_physics.mac
  -> /gate/run/initialize
  -> magiccube_production_digitizer.mac
  -> magiccube_production_source.mac
  -> MersenneTwister and 0–15 s acquisition
  -> verbose.mac
  -> magiccube_production_output.mac
  -> /gate/application/startDAQ
```

The frozen Step-5 geometry, system, physics, and digitizer are executed
unchanged. The Step-4 runtime system and Step-5 diagnostic macros are not
used.

## 12. Original Plate Omission

`plate.mac` is not ported. Its tungsten collimator is part of the original
physical detector architecture, whereas the Magic-Cube GAGG/K9 alternating
detector is the replacement self-collimating architecture. Omitting the
original physical plate is therefore forced by the detector replacement; no
tungsten, holes, or replacement collimator are introduced.

## 13. Files Created

- `magiccube_production_source.mac`
- `magiccube_production_output.mac`
- `magiccube_production_main.mac`
- `validate_magiccube_step6_preparation.py`
- `MAGIC_CUBE_STEP6_SOURCE_OUTPUT_MAIN_PORT.md`
- `MAGIC_CUBE_STEP6_RUNBOOK.md`

## 14. Frozen Files Confirmed Unchanged

The validator compares the current SHA-256 values with the eight values in
`MAGIC_CUBE_STEP5_CLOSURE_AUDIT.md` for the production geometry, production
system, production physics, production digitizer, `detector_map.csv`,
`magiccube_lattice_map.csv`, `magiccube_runtime_identity.json`, and
`magiccube_v1_config.json`. The expected preparation result is that all eight
match; a mismatch blocks Step 6. The corrected
`magiccube_production_source.mac` is now recorded by the Step-7 preparation
validator with SHA-256
`48e39d03f081cc4b95a9d065566743890e23fda4e8fcfc649d7f70ca70ea9c31`.

## 15. What Step 6 Proves

Step 6 proves only static faithful-port preparation: the verified source
values are preserved, the source transform is bounded to coordinates and
orientation, the active ROOT Tree/Hits output mechanism is retained, the four
Magic-Cube Singles collections are configured, the main order is explicit,
and the Step-5 hashes remain frozen.

## 16. What Step 6 Does NOT Prove

Step 6 does not prove:

- production macro runtime;
- final ROOT schema;
- final position-derived identity recovery;
- event statistics or source transport performance;
- PPDF correctness;
- system-matrix correctness;
- reconstruction correctness;
- scientific agreement with the paper or detector-response accuracy.

## 17. Step-7 Handoff

Step 7 is one bounded single-run end-to-end runtime validation of the Step-6
production workflow. It must execute the production-equivalent main macro in
a controlled harness, inspect the resulting ROOT schema, and verify whether
the frozen position-derived detector mapping can recover the 2048 canonical
channels. Step 7 is not implemented here.

## 18. Step-6 Status

`STEP 6 PREPARED: PASS` after the static validator passes. The bounded
source-frame correction supersedes the pre-correction preparation; runtime
remains intentionally unperformed.
