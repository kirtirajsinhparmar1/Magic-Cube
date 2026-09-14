# Magic-Cube Step 5 — Faithful Original Physics and Digitizer Port

## 1. Objective

Port the active original repository's physics and digitizer behavior to the
already validated Magic-Cube geometry. This document records the bounded
Step-5A/5B preparation only. It does not redesign the Monte Carlo method and
does not implement source production, production output, or the production
main macro.

## 2. Original Reference

Upstream repository: <https://github.com/spebt/mcsim>

The local checkout is the implementation authority used for this port:

- `GateParallel_NewConfiguration/GATE-Macro/physics.mac`
- `GateParallel_NewConfiguration/GATE-Macro/digitizer.mac`
- `GateParallel_NewConfiguration/GATE-Macro/system.mac` for the original SD
  attachment pattern
- `GateParallel_NewConfiguration/GATE-Macro/SPEBT.mac` for the original
  initialization order

The local original files were read directly before the new files were created.

## 3. Original Physics

The active original `physics.mac` contains exactly one enabled interaction:

```text
/gate/physics/addProcess PhotoElectric
/gate/physics/processes/PhotoElectric/setModel StandardModel
```

It then executes, in order:

```text
/gate/physics/processList Enabled
/gate/physics/processList Initialized
```

The active original macro does not add Compton, RayleighScattering,
ElectronIonisation, Bremsstrahlung, PositronAnnihilation, or
MultipleScattering. Their command lines are comments in the local file.

The original applies `1.0 cm` to each of the Gamma, Electron, and Positron
cuts in each of `xlayer1` through `xlayer8`. Commented phantom-specific cuts
are not part of the active detector behavior and were not ported.

## 4. Magic-Cube Physics Port

Created file: `magiccube_production_physics.mac`

The process commands and ordering are preserved. The only target adaptation is
the replacement of the eight original xlayer region names with the four
active Magic-Cube GAGG family names:

- `mc_gagg_ee`
- `mc_gagg_eo`
- `mc_gagg_oe`
- `mc_gagg_oo`

Each family receives the same original `1.0 cm` Gamma, Electron, and Positron
cut commands. K9 and Air are not given sensitive-detector-specific cut
commands. The frozen Step-4 no-system SD attachment remains in
`magiccube_runtime_system.mac`; it was not changed.

## 5. Original Digitizer

The active original `digitizer.mac` defines one `SinglesDigitizer` chain under
each original sensitive volume, `xlayer1` through `xlayer8`. Every chain has
this exact module order:

```text
adder -> energyResolution -> spatialResolution -> energyFraming
```

The exact active parameters are:

- energy resolution: `fwhm 0.10`
- energy reference: `140. keV`
- spatial resolution: `fwhm 1.0 mm`
- spatial confinement: `confineInsideOfSmallestElement true`
- spatial-resolution verbosity: `0`
- energy framing: `120. keV` through `160. keV`

The local active file contains no dead time, pile-up, efficiency, or
coincidence module.

## 6. Magic-Cube Digitizer Port

Created file: `magiccube_production_digitizer.mac`

The eight original xlayer command paths are adapted to four command paths,
one for each active GAGG family. Each family receives the complete original
11-command chain and the exact original parameter values. Because each GAGG
family is a repeated volume family, one family-level digitizer target covers
its repeated active copies.

The validated Step-4 system realization remains:

```text
/gate/<gagg-family>/attachCrystalSDnoSystem
```

No conventional scanner hierarchy was reintroduced. The compatibility status
is `MINOR_ADAPTATION_REQUIRED`: the command paths must be adapted from the
original xlayer SD names to the four Magic-Cube SD names, and the user must
perform the bounded real-GATE check because the Codex shell has no loaded GATE
runtime/source tree. No design-level detector-response replacement is used.

## 7. What Was Preserved Exactly

- PhotoElectric as the only active physics process.
- PhotoElectric `StandardModel`.
- Original physics process-list order.
- Original `1.0 cm` Gamma, Electron, and Positron cut values.
- Original digitizer module order.
- Original energy resolution and `140. keV` reference.
- Original `1.0 mm` spatial resolution and confinement flag.
- Original `120–160 keV` energy framing.
- Original common `Singles` collection name for the bounded Tree check.
- The validated no-system Magic-Cube sensitive-detector realization.
- The frozen position-derived detector identity policy.

## 8. What Changed Only Because of Magic-Cube

- `xlayer1` through `xlayer8` physics targets became the four active GAGG
  family targets.
- Eight original detector digitizer chains became four family-level chains,
  because Magic-Cube has four active GAGG families and K9 is passive.
- The digitizer manager paths use the four Magic-Cube volume/SD names.

No physics process, cut value, response parameter, or normalization behavior
was changed for scientific preference.

## 9. What Was NOT Added

- No Compton process.
- No Rayleigh process.
- No electron ionization, bremsstrahlung, annihilation, or multiple scattering.
- No Livermore or Penelope physics replacement.
- No new detector-response model.
- No paper-specific energy resolution.
- No paper-specific `112–168 keV` window.
- No optical transport.
- No dead time, pile-up, efficiency, or coincidence processing.
- No source production port.
- No production output port.
- No system-matrix or normalization change.

## 10. Detector Identity

The Step-4 identity classification is `POSITION_DERIVED_REQUIRED`.

`detector_map.csv` remains authoritative:

```text
hit position -> detector_map.csv -> canonical detector_id 0..2047
```

The digitizer macro does not define or replace this convention. If the
runtime Singles output does not retain enough position information for this
mapping, that is a runtime validation finding to document; it is not a reason
to assume that a fixed `volumeID` component equals the canonical detector ID.

## 11. Validation Harness

`magiccube_step5_digitizer_check.mac` is a bounded diagnostic macro. It uses
the frozen `magiccube_geometry.mac` and `magiccube_runtime_system.mac`, the
new production physics and digitizer macros, and the established bounded
external smoke source:

- gamma at `140.0 keV`
- point source at `(0.0, 0.0, -66.0 mm)`
- activity `20000.0 becquerel`
- one-second acquisition

It enables Tree Hits and adds the original common `Singles` collection name.
It intentionally does not execute the original `output.mac`, because that
file is a future production-output port and has legacy output assumptions.

`magiccube_step5_digitizer_job.sh` supplies the recorded UB CCR module setup,
runs the macro only when the user submits it, records the Gate exit code, and
invokes `validate_magiccube_step5_outputs.py`. The output validator checks
Gate success, readable ROOT, non-empty Hits, non-empty Singles, and fatal
geometry/digitizer errors. It does not check efficiency or spectrum shape.

## 12. Runtime Status

**PREPARED — NOT YET RUNTIME VALIDATED**

Codex did not execute GATE or Slurm. A real user-side GATE run is required
before calling Step 5 a runtime pass.

## 13. Next Original-Pipeline Component

After successful Step-5 runtime validation, the next bounded implementation
component is the **production source/output/main-macro port**. It is not
implemented by this task. Parallel execution, ROOT merging, PPDF, system
matrix, normalization, plotting, and reconstruction remain out of scope.
