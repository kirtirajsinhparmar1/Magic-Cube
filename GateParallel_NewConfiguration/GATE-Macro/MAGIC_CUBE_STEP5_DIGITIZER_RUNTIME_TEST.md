# Magic-Cube Step-5 Digitizer Runtime Validation

## 1. Purpose

The production Magic-Cube geometry, cylindricalPET system registration,
PhotoElectric physics, and all four GAGG sensitive families have now been
validated by raw-Hits job `26104250`. This bounded runtime test reintroduces
the unchanged original digitizer and requests Singles using the identical
external source configuration.

## 2. Prior Runtime Evidence

Job `26104250` completed with Gate exit code 0:

- internal probes: 411 Hits total;
- external smoke source: 970 Hits total;
- all four GAGG families produced Hits;
- interpretation: `RAW_HITS_PATH_VALIDATED`.

That evidence is the A/B baseline. It must not be reinterpreted or repeated
by this task.

## 3. Controlled A/B Design

Baseline A is `magiccube_step5_hits_external.mac`:

- production geometry;
- production system;
- production physics;
- external isotropic 140-keV point source at `(0, 0, -66) mm`;
- one-second acquisition;
- Hits output only.

Test B is `magiccube_step5_digitizer_runtime_check.mac`:

- the same geometry, system, physics, source, RNG, and timing;
- one execution of unchanged `magiccube_production_digitizer.mac` after
  `/gate/run/initialize`;
- the same Hits output plus the shared `Singles` output request;
- a new output prefix under `runtime_validation/step5_digitizer`.

## 4. Frozen Digitizer

The production digitizer remains exactly four family-specific chains:

```text
Adder -> EnergyResolution -> SpatialResolution -> EnergyFraming
```

Preserved parameters:

- EnergyResolution FWHM: `0.10`;
- reference energy: `140 keV`;
- SpatialResolution FWHM: `1.0 mm`;
- `confineInsideOfSmallestElement true`;
- EnergyFraming: `120–160 keV`.

No Readout, DeadTime, PileUp, efficiency, or coincidence module is added.

## 5. Runtime Questions

The single user-run job asks only:

1. Does Gate still exit 0 with real external detector interactions?
2. Are raw Hits still non-zero with the digitizer present?
3. Does SpatialResolution process real pulses without the corresponding-system
   exception?
4. Are non-zero Singles produced after the full original chain?

## 6. Acceptance Criteria

Full runtime validation requires Gate exit code 0, no fatal/macro-abort or
corresponding-system error, total Hits greater than zero, and total Singles
greater than zero. Exact stochastic counts, efficiency, spectrum, and
resolution performance are intentionally not acceptance criteria.

## 7. Failure Classifications

The output validator emits exactly one of:

- `DIGITIZER_RUNTIME_VALIDATED`;
- `SPATIALRESOLUTION_RUNTIME_BLOCKED`;
- `RAW_HITS_LOST_WITH_DIGITIZER_PRESENT`;
- `HITS_PRESENT_BUT_NO_SINGLES`;
- `EARLIER_RUNTIME_FAILURE`;
- `VALIDATION_INCOMPLETE_ENVIRONMENT_ERROR`.

## 8. Detector Identity

`POSITION_DERIVED_REQUIRED` remains frozen. This bounded digitizer runtime
check does not make position-derived detector identity a hard acceptance
criterion. If suitable position branches are present, the validator reports
their availability; a dedicated identity closure check can follow successful
digitizer validation.

## 9. Status

**PREPARED — RUNTIME NOT YET VALIDATED**

Codex did not execute Gate or submit Slurm. The production files and the
validated Hits-only macro remain unchanged.
