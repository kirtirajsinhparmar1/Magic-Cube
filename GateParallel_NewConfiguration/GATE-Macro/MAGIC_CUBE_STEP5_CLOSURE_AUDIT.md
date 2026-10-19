# Magic-Cube Step-5 Closure Audit

## 1. Final Status

**STEP 5: PASS**

The final runtime classification is:

    DIGITIZER_RUNTIME_VALIDATED

The final production geometry, system registration, faithful physics port,
and original-style digitizer all completed a real GATE runtime with nonzero
Hits and Singles.

## 2. Step-5 Objective

Step 5 ported the active original-repository physics and digitizer behavior to
the Magic-Cube detector and made the minimum detector-architecture adaptation
required for the original `SpatialResolution` module to obtain a valid GATE
system.

The objective was faithful pipeline compatibility, not a new detector-response
model or a scientific validation against Ref. 29 performance.

## 3. Original Repository Behavior Preserved

The production physics preserves the active original behavior:

- `PhotoElectric` with `StandardModel` is enabled.
- `Compton` and `Rayleigh` are inactive.
- Gamma, electron, and positron cuts remain `1.0 cm`.

The production digitizer preserves the original active chain for each of the
four GAGG families:

    adder
        -> energyResolution
        -> spatialResolution
        -> energyFraming

The original parameters remain unchanged:

- Energy resolution FWHM: `0.10` at `140 keV`.
- Spatial resolution FWHM: `1.0 mm`.
- `confineInsideOfSmallestElement`: `true`.
- Energy framing: `120–160 keV`.

## 4. Why Production System Adaptation Was Required

The Step-4 `attachCrystalSDnoSystem` configuration was sufficient to produce
raw Hits, but it did not provide the corresponding GATE system required by
the original `SpatialResolution` digitizer.

The production path therefore uses an actual centered `cylindricalPET`
system hierarchy and ordinary `attachCrystalSD` for the four active GAGG
families. This is a GATE system/bookkeeping adaptation required by the
original digitizer; it does not change the digitizer parameters or add new
physics.

## 5. Production Geometry Adaptation

The final physical hierarchy is:

    world
      -> cylindricalPET
        -> panel
          -> module
            -> block
              -> magicCubeMother
                -> mc_gagg_ee
                -> mc_gagg_eo
                -> mc_gagg_oe
                -> mc_gagg_oo
                -> mc_k9_ee
                -> mc_k9_eo
                -> mc_k9_oe
                -> mc_k9_oo

The upper `cylindricalPET`/`panel`/`module`/`block` hierarchy is centered,
Air-only bookkeeping required to instantiate the original system relationship.
It is distinct from the physical Magic-Cube detector body.

Frozen wrapper dimensions and translations are:

| Volume | Material | Dimensions | Translation |
|---|---|---|---|
| `cylindricalPET` | Air | `Rmin=0 mm`, `Rmax=55 mm`, height `42 mm` | `0 0 0 mm` |
| `panel` | Air | `73.2 x 73.2 x 38.0 mm` | `0 0 0 mm` |
| `module` | Air | `71.2 x 71.2 x 36.0 mm` | `0 0 0 mm` |
| `block` | Air | `69.2 x 69.2 x 34.0 mm` | `0 0 0 mm` |
| `magicCubeMother` | Air | `67.2 x 67.2 x 32.0 mm` | `0 0 0 mm` |

Because every wrapper translation and the `magicCubeMother` translation are
zero, the GAGG/K9 local centers remain the same global centers as in the
frozen Magic-Cube geometry. The 2048 GAGG positions, 2048 K9 positions,
materials, dimensions, checkerboard, and repeaters are unchanged.

## 6. Final Production System

The production system is `cylindricalPET` with these registrations:

    rsector   -> panel
    module    -> module
    submodule -> block
    crystal   -> magicCubeMother

Sensitive detector registration is:

    mc_gagg_ee -> attachCrystalSD
    mc_gagg_eo -> attachCrystalSD
    mc_gagg_oe -> attachCrystalSD
    mc_gagg_oo -> attachCrystalSD

All K9 families remain passive and receive no sensitive detector.

Native GATE volume IDs are not treated as canonical Magic-Cube detector IDs.

## 7. Final Production Physics

File: `magiccube_production_physics.mac`

The active process configuration is:

    PhotoElectric
        StandardModel

`Compton`, `Rayleigh`, electron ionization, bremsstrahlung, positron
annihilation, and multiple scattering remain inactive as in the active
original physics configuration. The gamma, electron, and positron cuts are
each `1.0 cm`, applied to the four active GAGG family regions.

No new physics was introduced.

## 8. Final Production Digitizer

File: `magiccube_production_digitizer.mac`

Four chains are configured, one for each active GAGG family:

    mc_gagg_ee
    mc_gagg_eo
    mc_gagg_oe
    mc_gagg_oo

Each chain is:

    adder
        -> energyResolution
        -> spatialResolution
        -> energyFraming

with:

    energyResolution:
        fwhm = 0.10
        energyOfReference = 140 keV

    spatialResolution:
        fwhm = 1.0 mm
        confineInsideOfSmallestElement = true

    energyFraming:
        min = 120 keV
        max = 160 keV

The runtime result proves that this original-style chain executes on real
Magic-Cube pulses. It does not prove scientific accuracy of the response
parameters.

## 9. Raw-Hits Runtime Evidence

The bounded raw-Hits precursor was job `26104250`. It completed with Gate
exit code `0` and demonstrated nonzero Hits from both internal and external
sources:

| Test | ee | eo | oe | oo | Total | Gate exit |
|---|---:|---:|---:|---:|---:|---:|
| Internal 30-keV | 101 | 96 | 116 | 98 | 411 | 0 |
| External 140-keV | 261 | 230 | 226 | 253 | 970 | 0 |

Classification:

    RAW_HITS_PATH_VALIDATED

This independently established that the production geometry, cylindricalPET
system, four `attachCrystalSD` targets, PhotoElectric physics, and both
source paths can generate raw detector interactions.

## 10. Final Digitizer Runtime Evidence

The final digitizer runtime was job `26104650` under GATE 9.4 and Geant4
11.2.1. Slurm reported `COMPLETED`, `ExitCode = 0:0`, and elapsed time
`00:00:22`. Gate exit code was `0`.

| Collection | ee | eo | oe | oo | Total |
|---|---:|---:|---:|---:|---:|
| Hits | 254 | 239 | 230 | 258 | 981 |
| Singles | 254 | 239 | 230 | 258 | 981 |

The final log contained no `GateSpatialResolution` corresponding-system
failure, no fatal/error patterns, no `COMMAND NOT FOUND`, and no macro abort.

Classification:

    DIGITIZER_RUNTIME_VALIDATED

The equal Hits and Singles totals are reported observations only. They do not
prove perfect detector efficiency, digitizer accuracy, or paper-level
detector performance.

## 11. Debugging History

These jobs are historical debugging evidence and are superseded by the final
runtime; none is a current blocker.

- `26030041`: the no-system `attachCrystalSDnoSystem` path reached
  `GateSpatialResolution::Digitize` and failed because no corresponding GATE
  system was available.
- `26037283`: Gate was not found in the Slurm environment; exit `127`. This
  was a wrapper/environment failure, not a physics, system, or digitizer
  failure.
- `26037645`: the production system macro attempted to attach a level before
  an actual `cylindricalPET` production hierarchy existed; Gate reported
  `COMMAND NOT FOUND` and exited `255`. This led to the centered Air-only
  wrapper hierarchy.
- `26040149`: system registration and acquisition completed with Gate exit
  `0`, but the then-unisolated run produced zero Hits and zero Singles. The
  later raw-Hits diagnostic job `26104250` superseded that observation by
  proving the production raw-Hits path.

## 12. Detector Identity

The canonical detector identity remains:

    POSITION_DERIVED_REQUIRED

The canonical formula remains:

    detector_id = d*256 + iy*16 + ix

with detector IDs in `0..2047`. The authoritative mapping remains:

    detector physical position
        -> detector_map.csv
        -> canonical detector_id

`detector_map.csv` and the canonical formula are unchanged. Step 4 previously
validated the position-derived identity method.

The Step-5 raw-Hits and final digitizer validators did not perform a new
position-derived identity test because suitable position branches were not
available in those diagnostic ROOT outputs. This does not invalidate the
Step-5 runtime result, but final production-output identity confirmation is
deferred to Step 6/7. The next production port must preserve enough output
information for downstream 2048-channel mapping.

## 13. Frozen Step-5 Files

The following SHA-256 values are the closure manifest for the frozen Step-5
production and identity artifacts.

| File | Purpose | SHA-256 |
|---|---|---|
| `magiccube_production_geometry.mac` | Centered Air-only production wrapper plus frozen Magic-Cube detector body | `3adf6843a7198889a4bc6ce07809fcf071af62111e1dfbb1e3535c29e8a880be` |
| `magiccube_production_system.mac` | `cylindricalPET` hierarchy registration and four GAGG SD attachments | `319019484bf798b7f294cc3ccb756d3e5c8c98b8cc013289b2e83a8c21e3fb76` |
| `magiccube_production_physics.mac` | Faithful PhotoElectric/StandardModel physics and cuts | `c56fc7e98a906d7a89e538e794456cf81f174d75078256dc55beaf72118a5df3` |
| `magiccube_production_digitizer.mac` | Four original-style GAGG Singles digitizer chains | `a8d96bc08ec38857667f0ec6621cb1d7b2c0651f15aa77619be71731579cd9b4` |
| `detector_map.csv` | Position-to-canonical-detector mapping | `dd7ca66a2b06bf091d229693bca48091d762a2d5c4508e12668ccfcaf363849c` |
| `magiccube_lattice_map.csv` | Frozen 4096-position lattice/material map | `a81702367aaa786fb08f4e4839e5c2f9834881f4b39d4574a53e0c6986902533` |
| `magiccube_runtime_identity.json` | Step-4 runtime identity and ROOT-schema evidence | `a4432b31948e07b189efa041654f93dbe2affa271d2d1d7104e5bbba8f04d62d` |
| `magiccube_v1_config.json` | Frozen Magic-Cube V1 configuration | `ce62fe60f4d19c38f7c19d62cf8d992e3acbf67d4674527377ef0d59d2a53aa8` |

## 14. What Step 5 Proves

The combined static and runtime evidence proves:

- The production hierarchy is accepted by GATE.
- The four GAGG sensitive-detector families are operational.
- K9 remains passive.
- The production PhotoElectric physics initializes and runs.
- Internal and external source interactions produce raw Hits.
- The original-style digitizer executes with real detector pulses.
- The `SpatialResolution` corresponding-system blocker is resolved.
- Nonzero Singles are generated for all four GAGG-family collections in the
  final bounded runtime.

## 15. What Step 5 Does NOT Prove

Step 5 does not prove:

- Paper-level sensitivity.
- Energy-resolution accuracy.
- Spatial-resolution accuracy.
- The final source/FOV production workflow.
- Complete 2048-channel downstream extraction.
- PPDF correctness.
- System-matrix correctness.
- Reconstruction correctness.
- Availability of final production-output branches needed for identity
  mapping.

## 16. Frozen Decisions

The following are frozen at Step-5 closure:

- Production geometry: **FROZEN**.
- Production system: **FROZEN**.
- Production physics: **FROZEN**.
- Production digitizer: **FROZEN**.
- Canonical detector identity: **FROZEN**.

Any later modification requires an explicit reason and new validation.

## 17. Step-6 Handoff

Step 6 objective only:

    port the original active source/output/main-macro workflow to the frozen
    Magic-Cube production geometry/system/physics/digitizer

Step 6 must preserve enough output information to recover the 2048 canonical
detector channels using `POSITION_DERIVED_REQUIRED`, or another explicitly
validated equivalent mapping. Step 6 is not implemented by this closure.

## 18. Final Closure Decision

    STEP 5 CLOSED: PASS
