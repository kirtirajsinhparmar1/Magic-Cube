# Magic-Cube Step-4 Closure Audit

## 1. Executive Status

**STEP 4 CLOSED — PASS**

The successful runtime job was Slurm job 25779143. Its actual geometry, probe,
and smoke-run banners report GATE 9.4 and Geant4 11.2.1. The runtime identity
classification is POSITION_DERIVED_REQUIRED.

    Step4Status: PASS
    RuntimeIdentity: POSITION_DERIVED_REQUIRED
    ProbeCount: 32
    ProbeFailures: 0
    Smoke140keV: PASS

This closure is based on runtime artifacts, status JSON, ROOT output headers,
the inspector observations, and an independent detector-map and
position-mapping cross-check. It is not based solely on the top-level success
text.

## 2. Scope of Step 4

Step 4 establishes that the frozen Magic-Cube geometry is compatible with a
real GATE runtime, that the four GAGG families operate as sensitive detectors
while K9 remains passive, that raw ROOT Hits are emitted, that canonical
detector identity can be recovered robustly, and that one external 140-keV
source produces hits. It is a runtime-geometry, hit-output, and
detector-identity validation stage; it is not a production physics or imaging
performance stage.

## 3. Frozen Detector Contract

The mother is centered at (0, 0, 0) mm and measures 67.2 x 67.2 x 32.0 mm,
with x,y bounds [-33.6, +33.6] mm and z bounds [-16, +16] mm. The
source-facing surface is at z = -16 mm. The conceptual lattice has
ix, iy, k = 0..15, hence 4,096 positions, with 2 x 2 x 2 mm segments,
4.2-mm lateral pitch, and a 2.2-mm lateral gap.

The alternating checkerboard assigns GAGG when (ix + iy + k) % 2 == 0 and K9
otherwise, yielding 2,048 active GAGG cubes and 2,048 passive K9 cubes. Eight
repeated 8 x 8 x 8 families implement the lattice: mc_gagg_ee, mc_k9_ee,
mc_gagg_eo, mc_k9_eo, mc_gagg_oe, mc_k9_oe, mc_gagg_oo, and mc_k9_oo.
Their first-copy-center translations are used with cubicArray/autoCenter false.

The canonical downstream identity is independent of GATE copy-number ordering:

    detector_id = d * 256 + iy * 16 + ix, where d = 0..7

It spans IDs 0..2047. An independent audit of detector_map.csv found 2,048
rows and zero violations of this formula.

## 4. Runtime History and Corrections

### Attempt 1 — Job 25778972

The initial run exposed the CrystalSD system-membership requirement and an
invalid /gate/output/tree/singles/disable command. The bounded corrections were
to use attachCrystalSDnoSystem and remove that invalid Tree Singles command.

### Attempt 2 — Job 25779058

GATE raised GeomMgt0002 because mc_gagg_ee_phys was entirely outside
magicCubeMother_log. The cause was the default cubicArray autoCenter semantics.
All eight families were corrected with explicit autoCenter false.

### Attempt 3 — Job 25779143

The completed run reported bounded runtime generation complete, identity
classification POSITION_DERIVED_REQUIRED, and final runtime validation PASS.

## 5. Successful Runtime Workflow

The recorded workflow was: static/runtime geometry check; 32 targeted 30-keV
GAGG-center probes; ROOT schema and hit inspection; native-identity versus
position-identity classification; one external isotropic 140-keV smoke run;
and the final runtime validator. runtime_run_summary.json contains 33 records:
32 probe records and one smoke record. The separate geometry check recorded
exit code 0.

## 6. Probe Audit

probe_manifest.json and the 32 probe_XX.status.json files contain exactly the
index set 0..31: no missing and no duplicate probes. Every probe exited GATE
with code 0, used 30 keV, and had a source position equal to the expected GAGG
center from detector_map.csv. Each expected detector ID, ix, iy, d, physical
layer k, family, and (x,y,z) coordinate matched the detector map.

There are exactly eight probes per GAGG family. Within every family their local
conceptual coordinates are exactly (0,0,0), (1,0,0), (0,1,0), (0,0,1),
(7,0,0), (0,7,0), (0,0,7), and (7,7,7).

| Probe | Expected family | Detector ID | ix | iy | d | k | x (mm) | y (mm) | z (mm) | Gate exit code | Position mapping result |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 00 | mc_gagg_ee | 0 | 0 | 0 | 0 | 0 | -31.5 | -31.5 | -15.0 | 0 | 81 unique; expected ID |
| 01 | mc_gagg_ee | 2 | 2 | 0 | 0 | 0 | -23.1 | -31.5 | -15.0 | 0 | 81 unique; expected ID |
| 02 | mc_gagg_ee | 32 | 0 | 2 | 0 | 0 | -31.5 | -23.1 | -15.0 | 0 | 81 unique; expected ID |
| 03 | mc_gagg_ee | 256 | 0 | 0 | 1 | 2 | -31.5 | -31.5 | -11.0 | 0 | 81 unique; expected ID |
| 04 | mc_gagg_ee | 14 | 14 | 0 | 0 | 0 | 27.3 | -31.5 | -15.0 | 0 | 81 unique; expected ID |
| 05 | mc_gagg_ee | 224 | 0 | 14 | 0 | 0 | -31.5 | 27.3 | -15.0 | 0 | 81 unique; expected ID |
| 06 | mc_gagg_ee | 1792 | 0 | 0 | 7 | 14 | -31.5 | -31.5 | 13.0 | 0 | 81 unique; expected ID |
| 07 | mc_gagg_ee | 2030 | 14 | 14 | 7 | 14 | 27.3 | 27.3 | 13.0 | 0 | 81 unique; expected ID |
| 08 | mc_gagg_eo | 16 | 0 | 1 | 0 | 1 | -31.5 | -27.3 | -13.0 | 0 | 81 unique; expected ID |
| 09 | mc_gagg_eo | 18 | 2 | 1 | 0 | 1 | -23.1 | -27.3 | -13.0 | 0 | 81 unique; expected ID |
| 10 | mc_gagg_eo | 48 | 0 | 3 | 0 | 1 | -31.5 | -18.9 | -13.0 | 0 | 81 unique; expected ID |
| 11 | mc_gagg_eo | 272 | 0 | 1 | 1 | 3 | -31.5 | -27.3 | -9.0 | 0 | 81 unique; expected ID |
| 12 | mc_gagg_eo | 30 | 14 | 1 | 0 | 1 | 27.3 | -27.3 | -13.0 | 0 | 81 unique; expected ID |
| 13 | mc_gagg_eo | 240 | 0 | 15 | 0 | 1 | -31.5 | 31.5 | -13.0 | 0 | 81 unique; expected ID |
| 14 | mc_gagg_eo | 1808 | 0 | 1 | 7 | 15 | -31.5 | -27.3 | 15.0 | 0 | 81 unique; expected ID |
| 15 | mc_gagg_eo | 2046 | 14 | 15 | 7 | 15 | 27.3 | 31.5 | 15.0 | 0 | 81 unique; expected ID |
| 16 | mc_gagg_oe | 1 | 1 | 0 | 0 | 1 | -27.3 | -31.5 | -13.0 | 0 | 81 unique; expected ID |
| 17 | mc_gagg_oe | 3 | 3 | 0 | 0 | 1 | -18.9 | -31.5 | -13.0 | 0 | 81 unique; expected ID |
| 18 | mc_gagg_oe | 33 | 1 | 2 | 0 | 1 | -27.3 | -23.1 | -13.0 | 0 | 81 unique; expected ID |
| 19 | mc_gagg_oe | 257 | 1 | 0 | 1 | 3 | -27.3 | -31.5 | -9.0 | 0 | 81 unique; expected ID |
| 20 | mc_gagg_oe | 15 | 15 | 0 | 0 | 1 | 31.5 | -31.5 | -13.0 | 0 | 81 unique; expected ID |
| 21 | mc_gagg_oe | 225 | 1 | 14 | 0 | 1 | -27.3 | 27.3 | -13.0 | 0 | 81 unique; expected ID |
| 22 | mc_gagg_oe | 1793 | 1 | 0 | 7 | 15 | -27.3 | -31.5 | 15.0 | 0 | 81 unique; expected ID |
| 23 | mc_gagg_oe | 2031 | 15 | 14 | 7 | 15 | 31.5 | 27.3 | 15.0 | 0 | 81 unique; expected ID |
| 24 | mc_gagg_oo | 17 | 1 | 1 | 0 | 0 | -27.3 | -27.3 | -15.0 | 0 | 81 unique; expected ID |
| 25 | mc_gagg_oo | 19 | 3 | 1 | 0 | 0 | -18.9 | -27.3 | -15.0 | 0 | 81 unique; expected ID |
| 26 | mc_gagg_oo | 49 | 1 | 3 | 0 | 0 | -27.3 | -18.9 | -15.0 | 0 | 81 unique; expected ID |
| 27 | mc_gagg_oo | 273 | 1 | 1 | 1 | 2 | -27.3 | -27.3 | -11.0 | 0 | 81 unique; expected ID |
| 28 | mc_gagg_oo | 31 | 15 | 1 | 0 | 0 | 31.5 | -27.3 | -15.0 | 0 | 81 unique; expected ID |
| 29 | mc_gagg_oo | 241 | 1 | 15 | 0 | 0 | -27.3 | 31.5 | -15.0 | 0 | 81 unique; expected ID |
| 30 | mc_gagg_oo | 1809 | 1 | 1 | 7 | 14 | -27.3 | -27.3 | 13.0 | 0 | 81 unique; expected ID |
| 31 | mc_gagg_oo | 2047 | 15 | 15 | 7 | 14 | 31.5 | 31.5 | 13.0 | 0 | 81 unique; expected ID |

## 7. ROOT Output Audit

All 128 expected probe ROOT files and all four smoke ROOT files are present,
identified as ROOT files, and readable at the ROOT-header/TTree level with
uproot. Every file exposes a ROOT object named tree. The inspector's
successful-run payload analysis records usable positive-deposition hits in the
expected family file for all 32 probes.

The observed tree branches are:

    PDGEncoding, trackID, parentID, trackLocalTime, time, runID, eventID,
    sourceID, primaryID, posX, posY, posZ, localPosX, localPosY, localPosZ,
    momDirX, momDirY, momDirZ, edep, stepLength, trackLength, rotationAngle,
    axialPos, processName, comptVolName, RayleighVolName, volumeID[0]..volumeID[9],
    sourcePosX, sourcePosY, sourcePosZ, nPhantomCompton, nCrystalCompton,
    nPhantomRayleigh, nCrystalRayleigh, photonID, sourceType, decayType, gammaType

Thus the requested run/event/source fields, source-position fields, hit
position fields, energy deposition, and ten volume-ID-like fields are actually
available. There are no named hierarchy-ID branches beyond those generic
volumeID fields.

The complete diagnostic response matrix below gives tree entry counts. Each
expected-family file has 81 entries; each non-expected GAGG-family file has
zero entries for its targeted probe. This is a diagnostic routing result, not a
detector-performance measurement.

| Probe | Expected family | ee | eo | oe | oo |
| --- | --- | ---: | ---: | ---: | ---: |
| 00 | mc_gagg_ee | 81 | 0 | 0 | 0 |
| 01 | mc_gagg_ee | 81 | 0 | 0 | 0 |
| 02 | mc_gagg_ee | 81 | 0 | 0 | 0 |
| 03 | mc_gagg_ee | 81 | 0 | 0 | 0 |
| 04 | mc_gagg_ee | 81 | 0 | 0 | 0 |
| 05 | mc_gagg_ee | 81 | 0 | 0 | 0 |
| 06 | mc_gagg_ee | 81 | 0 | 0 | 0 |
| 07 | mc_gagg_ee | 81 | 0 | 0 | 0 |
| 08 | mc_gagg_eo | 0 | 81 | 0 | 0 |
| 09 | mc_gagg_eo | 0 | 81 | 0 | 0 |
| 10 | mc_gagg_eo | 0 | 81 | 0 | 0 |
| 11 | mc_gagg_eo | 0 | 81 | 0 | 0 |
| 12 | mc_gagg_eo | 0 | 81 | 0 | 0 |
| 13 | mc_gagg_eo | 0 | 81 | 0 | 0 |
| 14 | mc_gagg_eo | 0 | 81 | 0 | 0 |
| 15 | mc_gagg_eo | 0 | 81 | 0 | 0 |
| 16 | mc_gagg_oe | 0 | 0 | 81 | 0 |
| 17 | mc_gagg_oe | 0 | 0 | 81 | 0 |
| 18 | mc_gagg_oe | 0 | 0 | 81 | 0 |
| 19 | mc_gagg_oe | 0 | 0 | 81 | 0 |
| 20 | mc_gagg_oe | 0 | 0 | 81 | 0 |
| 21 | mc_gagg_oe | 0 | 0 | 81 | 0 |
| 22 | mc_gagg_oe | 0 | 0 | 81 | 0 |
| 23 | mc_gagg_oe | 0 | 0 | 81 | 0 |
| 24 | mc_gagg_oo | 0 | 0 | 0 | 81 |
| 25 | mc_gagg_oo | 0 | 0 | 0 | 81 |
| 26 | mc_gagg_oo | 0 | 0 | 0 | 81 |
| 27 | mc_gagg_oo | 0 | 0 | 0 | 81 |
| 28 | mc_gagg_oo | 0 | 0 | 0 | 81 |
| 29 | mc_gagg_oo | 0 | 0 | 0 | 81 |
| 30 | mc_gagg_oo | 0 | 0 | 0 | 81 |
| 31 | mc_gagg_oo | 0 | 0 | 0 | 81 |

## 8. GATE-Native Identity Findings

The tested GATE-native candidates were volumeID[0] through volumeID[9]. Across
the 32 selected target outputs, volumeID[0] and volumeID[1] are constant zero
and volumeID[3] through volumeID[9] are constant -1. volumeID[2] varies, but
it is not canonical detector ID: its values span family-specific ranges with
offsets (0..511, 1024..1535, 2048..2559, and 3072..3583) and encode a GATE
placement ordering rather than the frozen d*256 + iy*16 + ix identity.

ID_ONLY_VALIDATED was rejected because no native component equalled the
expected canonical detector ID over all 32 probes. ID_PLUS_FAMILY_VALIDATED was
also rejected: no raw component equalled the expected family-local 8 x 8 x 8
index under any of the six finite permutations of (rx, ry, rz) tested by the
inspector. In particular, volumeID[2] contains family-specific offsets and
ordering behavior, while the remaining components are constants or sentinels.

The native fields are therefore useful runtime observations but are not adopted
as the canonical downstream identity. This conclusion is based on the
observation CSV and inspector classification evidence, not on an assumed
meaning for legacy fixed volumeID indices.

## 9. Position-Derived Canonical Identity

The validated policy maps each hit position to detector_map.csv. For each GAGG
detector center (x_i, y_i, z_i), the inspector accepts a candidate when all
three conditions hold:

    abs(posX - x_i) <= 1.000001 mm
    abs(posY - y_i) <= 1.000001 mm
    abs(posZ - z_i) <= 1.000001 mm

This is the implemented 1-mm cube half-width plus the inspector's
1.0e-6-mm tolerance. The mapping uses the detector-map row's canonical ID,
whose formula is d * 256 + iy * 16 + ix.

An independent recount of the 2,592 successful-run probe observations gives:

| Metric | Count |
| --- | ---: |
| Mapped hits | 2,592 |
| Unmapped hits | 0 |
| Ambiguous hits | 0 |
| Hits mapped to expected detector | 2,592 |
| Hits mapped to wrong detector | 0 |

For every individual probe, 81 hits map uniquely to its expected detector. The
expected and recovered probe IDs are identical:

    0, 2, 32, 256, 14, 224, 1792, 2030,
    16, 18, 48, 272, 30, 240, 1808, 2046,
    1, 3, 33, 257, 15, 225, 1793, 2031,
    17, 19, 49, 273, 31, 241, 1809, 2047

Thus POSITION_DERIVED_REQUIRED was selected because positions recover the
canonical identity uniquely and without mismatch. UNRESOLVED was avoided
because the position map is uniquely valid for every relevant probe hit. The
32 probes validate selected positions across four families, several local
axes, near/far repeat indices, and shallow/deep placements; they do not test
all 2,048 detector IDs individually.

## 10. 140-keV External Smoke Test

smoke_140kev.status.json exists and records Gate exit code 0. The macro uses a
point source at (0, 0, -66) mm, monoenergetic 140-keV photons, and an isotropic
angular distribution. All four GAGG ROOT files are readable. Their raw tree
entry counts are:

| Family | Hits |
| --- | ---: |
| mc_gagg_ee | 295 |
| mc_gagg_eo | 235 |
| mc_gagg_oe | 220 |
| mc_gagg_oo | 265 |
| **Total** | **1,015** |

This proves that the external source can transport through the completed
runtime geometry and generate GAGG hits. It is not a sensitivity, absolute
efficiency, cps/MBq, FWHM, or imaging-performance result.

## 11. Final Step-4 Validation Checklist

| Check | Result | Evidence |
| --- | --- | --- |
| Static geometry | PASS | Static validator: 4,096 placements, 2,048 GAGG, 2,048 K9, zero duplicates/outside placements |
| Runtime geometry | PASS | geometry_check.exit_code = 0; completed job 25779143 |
| GAGG sensitive | PASS | attachCrystalSDnoSystem applied to all four GAGG families; probe hits present |
| K9 passive | PASS | No K9 CrystalSD attachment; identity report records zero K9-sensitive hits |
| All 32 probes | PASS | Exact indices 0..31; all exit code 0 |
| ROOT readable | PASS | 128 probe and 4 smoke ROOT files expose readable tree objects |
| Position mapping | PASS | 2,592/2,592 probe observations uniquely map to detector-map entries |
| Ambiguous mapping | PASS | 0 ambiguous hits |
| Detector-ID consistency | PASS | 32/32 expected probe IDs recovered; zero canonical-formula errors in detector map |
| Smoke exit | PASS | smoke_140kev.status.json exit code 0 |
| External hits | PASS | 1,015 smoke Hits across four GAGG ROOT files |
| Final validator | PASS | Successful runtime output reports Magic-Cube Step-4 runtime validation: PASS |

## 12. What Step 4 Proves

- The 4,096 intended placements are runtime-compatible with real GATE.
- The four GAGG families can operate as sensitive detectors and emit ROOT Hits.
- K9 remains passive in this Step-4 configuration.
- All 32 diagnostic probes execute successfully and produce usable expected-family hits.
- The position-derived canonical detector identity policy works for all selected probe hits without ambiguity.
- An external isotropic 140-keV point source at the nominal source plane produces detector hits.
- The final Step-4 validator passes.

## 13. What Step 4 Does NOT Prove

- Exact K9 attenuation at 140 keV.
- Final electromagnetic transport fidelity or production cuts.
- Experimental sensitivity, paper cps/MBq, or absolute efficiency.
- Energy resolution or final 112–168-keV energy acceptance.
- Final multi-crystal/multihit event-handling policy.
- System-matrix accuracy, MLEM reconstruction, or paper spatial resolution.
- Agreement with paper experimental performance.

## 14. Frozen Runtime Identity Policy

Canonical detector identity for downstream work is derived from hit position plus
detector_map.csv unless a future deliberate, separately validated change
replaces this policy. Use the map's detector_id = d*256 + iy*16 + ix value.
Do not use legacy fixed volumeID indices as a canonical detector identifier.

## 15. Residual Risks / Deferred Items

- K9 is a material proxy whose attenuation accuracy remains a future physics-validation item.
- The Step-4 physics macro is deliberately diagnostic: it enables only the gamma PhotoElectric process with StandardModel; production electromagnetic physics and cuts remain deferred.
- There is no optical-photon transport, final digitizer, energy blur, 112–168-keV final energy window, or validated final multihit policy.
- The production source-emission model, system matrix, reconstruction, and experimental-performance comparisons remain out of scope.
- environment.txt contains a preliminary helper-version line reporting Gate 9.2, but the actual geometry/probe/smoke runtime banners and loaded module path report Gate 9.4 with Geant4 11.2.1. Runtime banners are the authority for this closure; future provenance capture should avoid that conflicting helper line.

## 16. Step-4 Closure Decision

**PASS.** Runtime geometry, sensitive-detector operation, raw ROOT Hits,
position-derived detector identity, and the bounded external 140-keV smoke test
all have artifact-backed passing evidence. Step 4 may be considered frozen.

No Step-5 work was performed during this audit.

