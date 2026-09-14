# Magic-Cube V1 Frozen Configuration Specification

## 1. Purpose and Scope

This document freezes the Step-1 configuration and detector-indexing contract for the main Ref. 29 Magic-Cube configuration from “A Self-Collimating Hand-held Intraoperative Gamma Camera with a Sparse Cubic Scintillator Detector Architecture.” It is specification only. It does not implement GATE geometry, materials, source, digitizer, physics, output, execution, or reconstruction.

V1 is an idealized gamma-transport detector: sparse GAGG elements eventually detect and attenuate photons reaching downstream GAGG elements, while K9 segments eventually provide passive transport material. Only the main Ref. 29 configuration is in scope. Low-Energy, Broad-Energy, Telephoto-Lens, and other variants are excluded.

V1 excludes SiPM boards, ASIC/ADC/FPGA electronics, housing, optical readout and optical-photon transport, flood-map/DOI electronics, and BaSO4. The nominal 2.2-mm lateral spaces and source-to-detector region are Air. No mechanical tungsten or lead plate/collimator is part of V1.

## 2. Source of Decisions

### Paper-specified quantities

The scientific inputs are the main Ref. 29 Magic-Cube design, nominal 67.2 mm × 67.2 mm × 32.0 mm detector volume, 16 × 16 lateral arrangement, 4.2-mm pitch, 2-mm material segments, 16 physical depth segments, alternating GAGG/K9 architecture, and the future Tc-99m/140-keV target.

### Professor-approved simplifications

- Work on the main Ref. 29 configuration first.
- Ignore SiPM, ASIC, ADC, FPGA, electronics, housing, and optical transport.
- Ignore BaSO4 for now.
- Treat lateral spaces and the source region as Air.
- Choose the negative-z detector face as source-facing.
- Exact experimental checkerboard parity is not required; use one deterministic parity.
- Scattered/multi-crystal events may be ignored in the first simple physics-development model, but this is not implemented in Step 1.

### V1 implementation conventions

The center is (0, 0, 0) mm, indices are zero-based, and negative z is source-facing. GAGG is selected when (ix + iy + k) % 2 == 0, making (0,0,0) GAGG. The parity, sign, coordinates, and canonical detector IDs below are implementation conventions, not claims about experimentally reported parity/orientation. The canonical ID is independent of any future GATE volumeID array position.

## 3. Global Coordinate System

x and y are lateral directions and z is depth. The mother center is (0, 0, 0) mm. Mother limits are x=[-33.6,+33.6] mm, y=[-33.6,+33.6] mm, and z=[-16.0,+16.0] mm. The source-facing nominal surface is z=-16.0 mm and the rear surface is z=+16.0 mm.

## 4. Detector Mother Volume

The nominal mother is a box of 67.2 mm × 67.2 mm × 32.0 mm, centered at (0,0,0) mm, with half extents 33.6, 33.6, and 16.0 mm. The mother/source region is Air for V1. Future GATE work must validate containment and overlaps.

## 5. Lateral Bar Lattice

There are 16 x positions and 16 y positions, hence 256 bars.

    ix = 0 ... 15
    iy = 0 ... 15
    x(ix) = (ix - 7.5) * 4.2 mm
    y(iy) = (iy - 7.5) * 4.2 mm

The centers on either lateral axis are -31.5, -27.3, -23.1, -18.9, -14.7, -10.5, -6.3, -2.1, +2.1, +6.3, +10.5, +14.7, +18.9, +23.1, +27.3, and +31.5 mm. Each segment is 2.0 mm × 2.0 mm laterally. The nominal free interval is 4.2-2.0=2.2 mm and is Air. The outer material edge is 31.5+1.0=32.5 mm, leaving 33.6-32.5=1.1 mm nominal outer margin per lateral side.

## 6. Depth Structure

There are 16 physical material layers, each 2.0 mm thick.

    k = 0 ... 15
    z(k) = (k - 7.5) * 2.0 mm

The layer centers are -15, -13, -11, -9, -7, -5, -3, -1, +1, +3, +5, +7, +9, +11, +13, and +15 mm for k=0 through 15. Adjacent depth segments touch without a nominal longitudinal Air gap.

## 7. GAGG/K9 Checkerboard Rule

For every conceptual position:

    parity = (ix + iy + k) % 2
    parity == 0 -> GAGG
    parity == 1 -> K9

Thus (ix=0,iy=0,k=0) is GAGG; changing x, y, or k flips the material. Layer k=0 begins G K G K ... / K G K G ..., while layer k=1 begins K G K G ... / G K G K .... This single parity is frozen; alternatives are not tested in Step 1.

For each bar, p=(ix+iy)%2 and the active GAGG layer for d=0...7 is:

    k_GAGG = 2*d + p

Even ix+iy bars use k=0,2,4,6,8,10,12,14; odd bars use k=1,3,5,7,9,11,13,15.

## 8. Material Counts / Geometry Invariants

    total lattice positions = 4096
    total GAGG = 2048
    total K9 = 2048
    GAGG per physical layer = 128
    K9 per physical layer = 128
    bars = 256
    GAGG per lateral bar = 8
    K9 per lateral bar = 8

Every one of the 4096 positions has exactly one material assignment, and only GAGG positions become active detector elements later.

## 9. Canonical Indexing

Indices are ix=0...15, iy=0...15, k=0...15, d=0...7, and p=(ix+iy)%2. The all-material index is:

    lattice_linear_index = k * 256 + iy * 16 + ix

It spans 0...4095 and identifies every GAGG/K9 position; it is not a detector ID. For active GAGG:

    k = 2*d + ((ix + iy) % 2)
    detector_id = d * 256 + iy * 16 + ix
    x_mm = (ix - 7.5) * 4.2
    y_mm = (iy - 7.5) * 4.2
    z_mm = (k - 7.5) * 2.0

Detector IDs are exactly 0...2047, with ix fastest, iy next, and d slowest. Later GATE copy numbers/hierarchy IDs must be mapped to this contract and runtime-validated; they must not redefine it.

## 10. Canonical Detector-ID Examples

| ix | iy | d | p | GAGG k | detector_id |
|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 | 0 | 0 |
| 1 | 0 | 0 | 1 | 1 | 1 |
| 15 | 0 | 0 | 1 | 1 | 15 |
| 0 | 1 | 0 | 1 | 1 | 16 |
| 15 | 15 | 0 | 0 | 0 | 255 |
| 0 | 0 | 1 | 0 | 2 | 256 |
| 15 | 15 | 7 | 0 | 14 | 2047 |

## 11. Source/FOV Convention for Future Steps

No source is implemented in Step 1. Future targets are Tc-99m, nominal 140 keV, finite diameter 0.7 mm (radius 0.35 mm), isotropic emission, and a 100 mm × 100 mm planar FOV parallel to the detector x-y face. It is 50 mm from the negative-z detector surface, so z_FOV=-16-50=-66 mm. Future coarse spacing is 2 mm × 2 mm with approximately 50 × 50 = 2500 locations. The final reconstruction grid is 1 mm and the future paper window is 112–168 keV. Exact coarse-grid endpoints and coordinates are DEFERRED TO SOURCE-MAP STEP.

## 12. Material Roles

- GAGG: future sensitive detector material; present in the existing local database.
- K9: future passive material; approved elemental composition is not locally present and is DEFERRED TO STEP 2. No composition is invented here.
- Air: future mother, lateral-gap, and source-region material; present in the existing local database.

K9 receives no detector_id. Its deterministic location is given by (ix,iy,k), parity, and, if needed, lattice_linear_index.

## 13. Explicit V1 Exclusions

- Mechanical tungsten or lead plate/collimator.
- BaSO4 reflector.
- SiPM boards, optical coupling, ASIC, ADC, FPGA, electronics, and readout chains.
- Housing.
- Optical-photon transport and optical readout.
- Low-Energy, Broad-Energy, Telephoto-Lens, and other alternate Magic-Cube configurations.

## 14. Future Physics Policy

No physics macro is changed. The future first physics-development model records 140-keV gamma, simplest interpretable direct/photoelectric-focused behavior, and initially ignored scattered multi-crystal events. Later work may add Compton, Rayleigh, realistic energy response, and multi-crystal handling. These are recorded only and are not implemented or tuned in Step 1.

## 15. Future System-Matrix Contract

The later experimental definition is c_ij = n_ij / (T_j * A_j), where i is detector, j is source/image location, n is the count, T is acquisition time, and A is activity. Monte Carlo must first preserve raw_count_ij and likely P_ij = raw_count_ij / N_emitted_j. Absolute/raw response must not be destroyed. Legacy detector-wise normalization over source positions must not define the Magic-Cube matrix. Existing system-matrix code is unchanged in Step 1.

## 16. Deferred Decisions

The following are intentionally DEFERRED / NOT PART OF STEP 1:

1. Exact K9 elemental composition — Step 2.
2. Actual GATE logical-volume hierarchy — geometry/system implementation.
3. GATE copy-number/hierarchy-ID to canonical detector_id mapping — later runtime validation.
4. Sensitive-detector attachment method — system implementation.
5. GATE/Geant4/ROOT module environment — runtime-readiness step.
6. Writable production output path — pipeline/runtime step.
7. Exact source-grid endpoints — source-map step.
8. Explicit random-seed formula — orchestration step.
9. Full event-selection logic — digitizer/physics step.
10. Energy-resolution implementation — digitizer step.
11. 112–168 keV energy framing — digitizer step.
12. MLEM/reconstruction — later.
13. BaSO4, SiPM/PCB/electronics/housing, and full optical simulation — intentionally ignored for V1.
14. Exact paper checkerboard orientation — not required; V1 parity is frozen here.
15. Alternative Magic-Cube configurations — not part of V1.

## 17. Geometry Invariants for Future Validation

Future code MUST assert: mother size 67.2×67.2×32.0 mm and center (0,0,0); 16×16×16 indices; 4.2-mm pitch; 2×2×2-mm segments; 2.2-mm lateral Air gap; x/y center extrema ±31.5 mm; lateral material edges ±32.5 mm; outer margin 1.1 mm; depth centers -15...+15 mm at 2-mm increments; touching depth segments; exactly one material per (ix,iy,k); 128 GAGG and 128 K9 per physical layer; 8 GAGG and 8 K9 per bar; totals 4096/2048/2048; valid GAGG k=2*d+((ix+iy)%2); detector IDs exactly unique 0...2047; no K9 detector IDs; all-material index 0...4095; source surface z=-16 mm; future FOV z=-66 mm. GATE overlap, hierarchy, attachment, output schema, and copy-number behavior remain runtime validations.

## 18. Frozen Step-1 Decisions

| Contract item | Frozen decision |
|---|---|
| Reference | Main Ref. 29 Magic-Cube only |
| Mother | 67.2 × 67.2 × 32.0 mm, center (0,0,0) |
| Axes/orientation | x/y lateral, z depth, negative-z source face |
| Lattice | 16×16 bars, 16 depth layers, 4.2-mm pitch |
| Segment | 2.0×2.0×2.0 mm³ |
| Gap | 2.2 mm Air laterally; depth segments touch |
| Pattern | GAGG iff (ix+iy+k)%2==0, otherwise K9 |
| Counts | 2048 GAGG, 2048 K9; 128/128 per layer; 8/8 per bar |
| Detector IDs | d*256+iy*16+ix, active GAGG only, 0...2047 |
| Lattice index | k*256+iy*16+ix, all positions, 0...4095 |
| Future source | Tc-99m, 140 keV, 0.7-mm diameter, isotropic, z_FOV=-66 mm |
| Future matrix | Preserve raw/absolute response; no legacy detector-wise normalization |

## 19. Change-Control Rule

Any future change to dimensions, pitch, parity, coordinate convention, or detector-ID mapping must be deliberate and update both:

    MAGIC_CUBE_V1_SPEC.md
    magiccube_v1_config.json

Future GATE macros must be generated and validated against these specifications, not independently redefine them.

