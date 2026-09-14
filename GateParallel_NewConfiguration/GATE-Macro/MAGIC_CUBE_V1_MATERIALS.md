# Magic-Cube V1 Material Contract

## 1. Purpose

This document records Step 2 of the controlled Magic-Cube implementation. Step 1 froze the detector geometry, coordinates, checkerboard pattern, and canonical detector indexing. Step 2 establishes only the material names and the provisional K9 strategy; it does not begin geometry implementation.

## 2. Scientific Role of the Materials

- **GAGG** is the active scintillator. It detects gamma interactions and also provides the upstream attenuation/self-collimation behavior of the sparse detector.
- **K9** is passive light-guide material in the physical detector. It is intended to be comparatively less attenuating than GAGG, alternates with GAGG, and is not a sensitive detector.
- **Air** is used for the V1 mother volume, lateral gaps, and source region.

Optical-photon transport and optical readout remain excluded from V1.

## 3. Paper-Reported Material Targets

The following are approximate paper-reported targets, not results of this Step 2 implementation:

| Material | Density target | Approximate attenuation at 140 keV |
|---|---:|---:|
| GAGG | ~6.6 g/cm3 | ~4.7 cm^-1 |
| K9 | ~2.5 g/cm3 | ~0.4 cm^-1 |

## 4. Existing Repository Material Definitions

The relevant definitions in `GateMaterials.db` in the current Step-2 state are:

| Material | Current lines | Density | Components |
|---|---:|---:|---|
| GAGG | 121–125 | 6.63 g/cm3 | Gadolinium n=3; Aluminium n=2; Gallium n=3; Oxygen n=12 |
| Air | 155–160 | 1.29 mg/cm3 | Nitrogen f=0.755268; Oxygen f=0.231781; Argon f=0.012827; Carbon f=0.000124 |
| Glass | 161–165 | 2.5 g/cm3 | Sodium f=0.1020; Calcium f=0.0510; Silicon f=0.2480; Oxygen f=0.5990 |
| K9_V1_PROXY | 167–171 | 2.5 g/cm3 | Sodium f=0.1020; Calcium f=0.0510; Silicon f=0.2480; Oxygen f=0.5990 |

Exact K9 was not present before Step 2. `K9_V1_PROXY` copies the local generic `Glass` definition exactly; it is not a relabeling of `Glass` and does not establish that `Glass` is the experimental K9.

## 5. K9 V1 Decision

`K9_V1_PROXY` is a **PROVISIONAL** gamma-transport material. Its density and elemental composition are copied from the repository's generic `Glass` material so that controlled V1 geometry and early physics-development work can proceed.

This proxy is **not exact paper K9** and is not author- or manufacturer-verified. It must not be described as having the paper attenuation coefficient of approximately 0.4 cm^-1. That value is a future validation target only.

## 6. GateMaterials.db Mapping

| Conceptual material | GATE material |
|---|---|
| GAGG | `GAGG` |
| K9 | `K9_V1_PROXY` |
| Gap | `Air` |
| Mother | `Air` |
| Source region | `Air` |

## 7. Material Roles in Future Geometry

Only GAGG becomes sensitive. `K9_V1_PROXY` is passive, and Air is passive. No detector IDs are assigned to K9 or Air.

## 8. Quantitative Validation Still Required

Before using V1 for paper-level sensitivity matching, a later controlled material-physics test must measure simulated transmission/attenuation at 140 keV for both GAGG and `K9_V1_PROXY`.

The results must be compared with the approximate paper targets:

- GAGG: ~4.7 cm^-1
- K9: ~0.4 cm^-1

If `K9_V1_PROXY` is substantially inconsistent, it must be replaced with a better author/manufacturer-supported definition. No such GATE test is performed in Step 2.

## 9. What Step 2 Does NOT Validate

- Photon cross sections.
- Attenuation coefficients.
- Compton behavior.
- Rayleigh behavior.
- Energy spectrum.
- Detector efficiency or sensitivity.
- Geometry, source, or GATE hierarchy.
- Optical behavior.
- The real K9 manufacturer formulation.

## 10. Future Upgrade Path

The current material mapping is:

    K9 -> K9_V1_PROXY

If an author- or manufacturer-verified K9 definition is obtained later, the mapping can be changed to that material without changing the conceptual geometry or indexing contract.

## 11. Frozen Step-2 Material Contract

| Concept | GATE Material | Role | Status |
|---|---|---|---|
| GAGG | `GAGG` | active | accepted V1 |
| K9 | `K9_V1_PROXY` | passive | provisional |
| Gap | `Air` | passive | accepted V1 |
| Mother | `Air` | passive | accepted V1 |
| Source region | `Air` | passive | accepted V1 |

## 12. Remaining Material Blocker for Paper-Level Matching

Exact/author-verified K9 composition remains unresolved.

- Blocker for initial V1 geometry testing: **NO**.
- Blocker for claiming exact paper-material replication: **YES**.
