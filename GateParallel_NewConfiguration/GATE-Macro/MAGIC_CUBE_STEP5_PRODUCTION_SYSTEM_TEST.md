# Magic-Cube Step-5 Production-System Candidate

## 1. Purpose

This document records one bounded production-system candidate for the
faithful Magic-Cube port. The candidate exists only to provide the valid
GATE system membership required by the unchanged original
`spatialResolution` digitizer module.

The previous candidate failed while parsing its system macro, before physics
initialization, digitizer initialization, or `SpatialResolution` execution.
This candidate tests the missing structural prerequisite; it does not alter
the original physics or digitizer behavior.

## 2. Previous Candidate and New Evidence

The previous runtime was job `26037645` under GATE 9.4 / Geant4 11.2.1. It
exited with code 255 on:

```text
***** COMMAND NOT FOUND
/gate/systems/cylindricalPET/rsector/attach magicCubeMother
```

The cause was that no physical volume hierarchy named `cylindricalPET`,
`panel`, `module`, and `block` existed when the production system macro was
executed. That candidate is rejected and is not repeated here.

## 3. Single Production Candidate

The new candidate inserts a centered, Air-only bookkeeping hierarchy above
the unchanged Magic-Cube detector body:

```text
world
└── cylindricalPET       Air cylinder, centered
    └── panel             Air box, centered
        └── module        Air box, centered
            └── block     Air box, centered
                └── magicCubeMother
                    └── existing eight mc_* families
```

The candidate uses the original `cylindricalPET` system and does not create a
second system type or an alternative detector architecture.

## 4. System Hierarchy

The production system macro registers exactly:

```text
rsector   -> panel
module    -> module
submodule -> block
crystal   -> magicCubeMother
```

The physical system-level wrappers are all centered at `(0, 0, 0)`. The
Magic-Cube mother is the system `crystal` level, and its four GAGG family
daughters are the sensitive detector volumes.

## 5. Sensitive Detector Registration

The production candidate uses ordinary `attachCrystalSD` on exactly:

```text
mc_gagg_ee
mc_gagg_eo
mc_gagg_oe
mc_gagg_oo
```

All four K9 families remain passive. No `attachCrystalSDnoSystem` command is
present in the production system macro. The validated Step-4 no-system
configuration remains frozen in `magiccube_runtime_system.mac`.

## 6. Geometry Preservation

The only new geometry is the centered Air wrapper hierarchy. The detector
body inside `magicCubeMother` is copied from the frozen
`magiccube_geometry.mac` without changing family definitions, dimensions,
materials, translations, repeat counts, repeat vectors, or `autoCenter`.

The wrapper dimensions are fixed for this candidate:

| Volume | Shape/material | Dimensions |
|---|---|---|
| `cylindricalPET` | Air cylinder | `Rmin=0 mm`, `Rmax=55 mm`, `height=42 mm` |
| `panel` | Air box | `73.2 x 73.2 x 38.0 mm` |
| `module` | Air box | `71.2 x 71.2 x 36.0 mm` |
| `block` | Air box | `69.2 x 69.2 x 34.0 mm` |
| `magicCubeMother` | Air box | `67.2 x 67.2 x 32.0 mm` |

Every wrapper translation is `0 0 0 mm`. Therefore each GAGG/K9 global
center is the same as in Step 4. The cylindrical radius and height contain
the centered panel, and each nested box has a 1 mm face clearance to its
parent.

## 7. K9 Behavior

K9 remains passive. The eight-family detector body remains 2048 GAGG plus
2048 K9 positions with the frozen checkerboard arrangement.

## 8. Original Physics Preservation

The candidate executes the unchanged `magiccube_production_physics.mac`.
It preserves the original PhotoElectric / StandardModel behavior, disabled
Compton and Rayleigh processes, and the original 1 cm particle cuts.

## 9. Original Digitizer Preservation

The candidate executes the unchanged `magiccube_production_digitizer.mac`.
All four GAGG chains retain the original sequence and parameters:

```text
adder
  -> energyResolution (fwhm 0.10, reference 140 keV)
  -> spatialResolution (fwhm 1.0 mm, confinement true)
  -> energyFraming (120--160 keV)
```

No module, resolution value, confinement setting, or framing limit was
changed.

## 10. Detector Identity

`POSITION_DERIVED_REQUIRED` remains the canonical runtime identity policy.
`detector_map.csv` and the formula
`detector_id = d*256 + iy*16 + ix` remain unchanged. Any GATE-native ID
bookkeeping produced by system registration is not treated as the canonical
Magic-Cube detector ID.

## 11. Runtime Validation Plan

`magiccube_step5_system_check.mac` uses the production-only geometry and
system files, the unchanged physics and digitizer files, and the bounded
140-keV smoke source. It requests both Hits and Singles and performs one
short acquisition. It does not execute the frozen Step-4 geometry or
runtime system macro and is not a production source or performance test.

The user-run job is `magiccube_step5_system_job.sh`; its output is directed
to the bounded runtime directory
`/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_system`.

## 12. Acceptance Criteria

The future manual run must establish, in order:

1. the wrapper volumes and all four system attachments parse successfully;
2. `/gate/run/initialize` succeeds;
3. ordinary `attachCrystalSD` succeeds for all four GAGG families;
4. the original digitizer reaches `SpatialResolution` without the missing
   system exception;
5. the Gate process exits with code 0;
6. Hits and Singles ROOT outputs exist and are non-empty when readable.

No sensitivity, spectrum, spatial-performance, PPDF, system-matrix, or
reconstruction criterion is part of this bounded test.

## 13. Status

**STATICALLY PREPARED — RUNTIME NOT YET VALIDATED**

This document does not claim that GATE accepts the candidate hierarchy at
runtime. The user must run exactly one bounded manual job to test that
hypothesis.
