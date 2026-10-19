# Magic-Cube Step-7 End-to-End Production Validation

## 1. Purpose

Step 7 validates the complete Step-6 production workflow.  The first exact
15-second serial attempt reached acquisition successfully but exceeded the
bounded Slurm wall-clock limit.  The runtime artifact prepared here therefore
uses a separate 1-second acquisition while preserving every other production
setting.

No scientific redesign is made here.  The test is bounded to one normal
production execution and does not measure sensitivity, resolution, or paper
agreement.

## 2. Frozen Foundation

Step 5 is closed PASS.  The cylindricalPET bookkeeping hierarchy, four GAGG
`attachCrystalSD` families, PhotoElectric-only physics, original-style
digitizer, and `POSITION_DERIVED_REQUIRED` identity policy are frozen.

The authoritative Step-5 runtime was job 26104650: Gate exit 0, 981 Hits,
and 981 Singles.  The raw-Hits precursor was job 26104250: 411 internal Hits
and 970 external Hits.

## 3. Step-6 Production Configuration

Step 6 prepared these unchanged artifacts:

- `magiccube_production_source.mac`: gamma, 140 keV, 0.0001 Ci, Plane /
  Rectangle, transformed source centre `(0, 0, -187.5) mm`, 250 mm half sizes,
  iso, theta 90--90 degrees, phi 150--210 degrees.
- `magiccube_production_output.mac`: ROOT tree output, Hits enabled, and the
  four production Singles collections.
- `magiccube_production_main.mac`: the original active orchestration with the
  Magic-Cube detector files substituted and the physical original plate
  omitted.

## 4. Exact Runtime Artifact

The real production artifact remains unchanged:

    magiccube_production_main.mac
    acquisition stop = 15 s

The bounded Step-7 validation artifact is:

    magiccube_step7_bounded_main.mac
    acquisition stop = 1 s

It is derived from the production main and differs only in the acquisition
stop time and the isolated output macro selection.  It is never used for
final production data.  The bounded output macro preserves the production
schema and collection settings while writing the relative prefix
`./magiccube_step7_bounded.root`, avoiding the existing production-prefix
timeout artifacts.

## 4a. Prior Exact-Production Runtime

Job `26105745` used the unchanged 15-second production main.  It reached
geometry, physics, source initialization, and acquisition start with no GATE
fatal error, then was killed by Slurm at the wall-clock limit.  The requested
15-second run corresponds to approximately 55.5 million primary decays.
This is a production-scale workload timeout, not a demonstrated simulation
compatibility failure.

## 4a. Bounded source-frame correction after job 26105689

Step-7 job `26105689` failed with Gate exit `255` during production source
parsing because GATE 9.4 did not recognize
`/gate/source/source1/gps/rot1`. Acquisition did not begin, no detector ROOT
event trees were produced, and detector identity was not tested. This is not
evidence of an identity-output insufficiency.

The source correction is limited to GATE namespace and source-direction
compatibility: positional rotation commands are under `gps/pos/rot1` and
`gps/pos/rot2`, while the angular frame uses `gps/ang/rot1 = (0,0,-1)` and
`gps/ang/rot2 = (0,1,0)`. The unchanged central `theta = 90 deg`,
`phi = 180 deg` direction is therefore +Z, toward the detector from the
source at `(0,0,-187.5) mm`. The theta/phi values, source statistics, center,
dimensions, acquisition, and RNG are unchanged. The identity status
therefore remains `UNKNOWN UNTIL SUCCESSFUL STEP-7 RUNTIME`.

Bounded Step-7 job `26109308` completed with Gate exit 0 and no GATE errors,
but produced zero Hits and zero Singles because its central angular direction
was -Z, away from the Magic-Cube detector. The final correction changes only
angular `rot1` from `(0,0,+1)` to `(0,0,-1)`; it is a source-direction
compatibility correction, not a scientific source redesign.

## 5. Runtime Questions

The one run answers:

1. Does the complete production macro execute successfully?
2. Are Hits and Singles present and non-empty?
3. What are the actual final Hits/Singles ROOT trees and branches?
4. Can canonical detector identity be recovered without treating native
   volume IDs as canonical IDs?

## 6. Production Source

The source preserves the active original source statistics: gamma,
monoenergetic 140 keV, activity 0.0001 Ci, Plane/Rectangle with 250 mm half
sizes, iso angular distribution, theta 90--90 degrees, phi 150--210 degrees,
15 s acquisition, MersenneTwister, and no explicit seed.  The only source
change is the Step-6 geometry-forced rigid coordinate transformation
`(x,y,z)_original -> (-z,y,x)_MagicCube`.

## 7. Production Output

The output macro enables the ROOT tree and Hits, uses the configured relative
file `./magiccube_production.root`, and requests:

- `Singles_mc_gagg_ee`
- `Singles_mc_gagg_eo`
- `Singles_mc_gagg_oe`
- `Singles_mc_gagg_oo`

The validator discovers actual tree/file names instead of assuming a single
monolithic ROOT file.

## 8. Identity Validation Strategy

The frozen policy is `POSITION_DERIVED_REQUIRED`.  When suitable physical
position branches exist, the runtime validator maps observations through the
unchanged `detector_map.csv` using the existing Step-4 per-coordinate
`1.01 mm` matching logic.  Native GATE volume IDs are reported as schema
metadata only and are never substituted for canonical detector IDs.

The validator separately reports whether Hits and Singles expose usable
position information.  If the final output lacks such branches, it reports
the identity limitation rather than modifying output in Step 7.

## 9. Runtime Acceptance Criteria

The production workflow must exit Gate 0 without a fatal abort, produce
nonzero Hits and Singles, and expose enough output information for canonical
identity recovery to receive the `STEP7_END_TO_END_VALIDATED` classification.
The runtime validator also writes `step7_root_schema.txt` under the Step-7
runtime directory.

The allowed overall classifications are:

- `STEP7_END_TO_END_VALIDATED`
- `STEP7_RUNTIME_VALID_IDENTITY_PENDING`
- `STEP7_PRODUCTION_RUNTIME_FAILED`
- `STEP7_OUTPUT_EMPTY`
- `STEP7_VALIDATION_ENVIRONMENT_ERROR`

The identity subclassification is one of:

- `PRODUCTION_IDENTITY_VALIDATED`
- `PRODUCTION_IDENTITY_OUTPUT_INSUFFICIENT`
- `PRODUCTION_IDENTITY_RUNTIME_AMBIGUOUS`
- `PRODUCTION_IDENTITY_NOT_CHECKED_ENVIRONMENT_ERROR`

## 10. What Step 7 Does Not Test

Step 7 does not test paper-level sensitivity, detector efficiency, energy or
spatial resolution accuracy, PPDF correctness, system-matrix construction,
reconstruction, parallel execution, or scientific agreement with Ref. 29.

## 11. Step-6 File Hashes

These hashes freeze the Step-6 source/output/main artifacts for this bounded
runtime preparation:

| File | SHA-256 |
|---|---|
| `magiccube_production_source.mac` | `48e39d03f081cc4b95a9d065566743890e23fda4e8fcfc649d7f70ca70ea9c31` |
| `magiccube_production_output.mac` | `d6df1bbe8c5717420fc89a5b61787a93a548d366856681ed185a23bc9e746831` |
| `magiccube_production_main.mac` | `e4c1a215c1a9a1430f961ecc98b23a3a0b00937bf0ed4aedd2422f9de112a95d` |

The Step-7 preparation validator also verifies all eight Step-5 closure
hashes before allowing the job to be submitted.

## 12. Validation Boundary

    magiccube_production_main.mac
        REAL PRODUCTION CONFIGURATION — 15 s

    magiccube_step7_bounded_main.mac
        VALIDATION ONLY — 1 s

A successful bounded run validates pipeline compatibility, ROOT production,
and schema inspection for the same workflow.  It does not establish
completion time or performance for the full 15-second workload.  The later
full/parallel workflow must use `magiccube_production_main.mac`, not the
bounded file.

## 13. Status

**PREPARED — BOUNDED RUNTIME NOT YET VALIDATED**

The next run must execute `magiccube_step7_bounded_main.mac` once with the
corrected source file. Job `26105689` remains historical source-parsing
failure evidence only, and job `26105745` remains historical production-scale
timeout evidence.
