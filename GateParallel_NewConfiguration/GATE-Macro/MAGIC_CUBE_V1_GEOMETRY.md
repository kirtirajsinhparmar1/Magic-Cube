# Magic-Cube V1 Geometry Implementation

## 1. Step-3 Purpose

Steps 1 and 2 froze the Magic-Cube V1 geometry/indexing and material
contracts. Step 3 translates those contracts into a deterministic GATE
geometry fragment and canonical lattice/detector maps. This step performs
static mathematical validation only; it does not execute GATE or Geant4.

The generated macro is a detector geometry fragment. It assumes that
`/gate/world` already exists and deliberately does not alter the world,
system hierarchy, physics, digitizer, source, or output configuration.

## 2. Inherited Scientific Geometry

The Ref. 29 V1 detector mother is 67.2 x 67.2 x 32.0 mm. Its conceptual
lattice is 16 x 16 x 16, with full material-segment dimensions of 2.0 x
2.0 x 2.0 mm. Lateral center pitch is 4.2 mm, giving a 2.2-mm nominal Air
surface gap. The checkerboard rule is:

```text
if (ix + iy + k) % 2 == 0: GAGG
else:                      K9
```

The intended counts are 2048 GAGG positions and 2048 K9 positions.

## 3. Coordinate System

The mother is centered at `(0, 0, 0)` mm with bounds x/y = [-33.6, +33.6]
mm and z = [-16.0, +16.0] mm. The source-facing side is negative z.

```text
x(ix) = (ix - 7.5) * 4.2 mm
y(iy) = (iy - 7.5) * 4.2 mm
z(k)  = (k - 7.5) * 2.0 mm
```

The center ranges are x/y = -31.5...+31.5 mm and z = -15...+15 mm.

## 4. Why Eight Families Are Used

The x index has two parity classes and the y index has two parity classes.
That gives four lateral groups: EE, EO, OE, and OO. Each lateral group
has one GAGG family and one K9 family:

```text
2 ix parities x 2 iy parities x 2 materials = 8 families
```

Each family is one 2-mm cubic seed plus an 8 x 8 x 8 `cubicArray`, so the
macro describes 512 repeated copies per family rather than thousands of
independent logical-volume definitions.

The family translations are frozen **first-copy centers**. This is an
implementation contract, not a change to the scientific geometry. GATE 9.4
creates a `cubicArray` with automatic centering enabled by default, which
would instead interpret each seed translation as the center of the complete
repeated array. The generated macro therefore explicitly issues
`/gate/<family>/cubicArray/autoCenter false` for all eight families so that
the seed remains the first placement and the repeat vector generates the
coordinates in the table below.

## 5. Exact Family Table

All repeat counts are X/Y/Z = 8/8/8, all repeat vectors are
8.4/8.4/4.0 mm, and every family has 512 intended copies.

| Family | ix parity | iy parity | Material | First x (mm) | First y (mm) | First z (mm) | Copies |
|---|---|---|---|---:|---:|---:|---:|
| `mc_gagg_ee` | even | even | GAGG | -31.5 | -31.5 | -15.0 | 512 |
| `mc_k9_ee` | even | even | K9_V1_PROXY | -31.5 | -31.5 | -13.0 | 512 |
| `mc_gagg_eo` | even | odd | GAGG | -31.5 | -27.3 | -13.0 | 512 |
| `mc_k9_eo` | even | odd | K9_V1_PROXY | -31.5 | -27.3 | -15.0 | 512 |
| `mc_gagg_oe` | odd | even | GAGG | -27.3 | -31.5 | -13.0 | 512 |
| `mc_k9_oe` | odd | even | K9_V1_PROXY | -27.3 | -31.5 | -15.0 | 512 |
| `mc_gagg_oo` | odd | odd | GAGG | -27.3 | -27.3 | -15.0 | 512 |
| `mc_k9_oo` | odd | odd | K9_V1_PROXY | -27.3 | -27.3 | -13.0 | 512 |

## 6. Family Geometry Derivation

Even x and y coordinates start at -31.5 mm; odd coordinates start at
-27.3 mm. Within a parity sublattice, the repeat pitch is 8.4 mm. A
given lateral parity has p = `(ix + iy) % 2`. For p = 0, GAGG starts at
z = -15.0 mm and K9 at -13.0 mm. For p = 1, those starts are exchanged.
Same-material depth repeats are separated by 4.0 mm, while adjacent
material-layer centers are separated by 2.0 mm.

## 7. Physical Material Geometry

Each material segment is a full 2 x 2 x 2 mm box. The 4.2-mm lateral
nearest-neighbor center spacing therefore leaves a 2.2-mm Air surface gap.
The outermost material edge is 32.5 mm from the center, leaving a 1.1-mm
nominal lateral margin to the 33.6-mm mother half-width. Sequential depth
segments have 2-mm thickness and 2-mm center spacing, so their faces touch
without a longitudinal Air gap or overlap.

## 8. Geometry Counts

| Quantity | Intended count |
|---|---:|
| Family count | 8 |
| Copies per family | 512 |
| GAGG families | 4 |
| GAGG total | 2048 |
| K9 families | 4 |
| K9 total | 2048 |
| All material positions | 4096 |

## 9. Canonical Lattice Index

Every conceptual `(ix, iy, k)` location receives:

```text
lattice_linear_index = k * 256 + iy * 16 + ix
```

It ranges from 0 through 4095 and covers both GAGG and K9. It is a
software map index, not a GATE copy number.

## 10. Canonical Detector ID

Only GAGG receives a canonical detector ID. For active GAGG depth
`d = 0...7`, the physical layer is:

```text
k = 2*d + ((ix + iy) % 2)
detector_id = d * 256 + iy * 16 + ix
```

This yields exactly 0...2047, with ix varying fastest, then iy, then d.
The canonical ID is independent of GATE runtime copy numbers, volumeID
arrays, replica ordering, and any cylindricalPET indexing.

## 11. Family-Local Conceptual Index

For documentation and map joins, each placement also has:

```text
family_rx = ix // 2
family_ry = iy // 2
family_rz = k // 2
family_local_index_conceptual = family_rz*64 + family_ry*8 + family_rx
```

Each component is 0...7 and the local index is 0...511 within its family.

**This is not a GATE copy ID.** Step 3 makes no claim about the internal
copy-number order produced by `cubicArray`.

## 12. Generated Files

- `magiccube_geometry.mac`: auto-generated GATE detector geometry fragment.
- `magiccube_lattice_map.csv`: all 4096 conceptual material locations.
- `detector_map.csv`: the 2048 active GAGG locations sorted by canonical ID.
- `generate_magiccube_geometry.py`: deterministic generator using the JSON
  configuration as its machine-readable source.
- `validate_magiccube_geometry.py`: standard-library static validator.

Generated macro and maps contain no timestamps, UUIDs, random values, or
claimed GATE copy IDs. They should not be hand-edited.

## 13. Material Mapping

```text
GAGG -> GAGG
K9   -> K9_V1_PROXY
mother/gaps -> Air
```

`K9_V1_PROXY` remains the provisional Step-2 proxy copied from generic
local `Glass`; it is not exact paper K9 and has not been attenuation
validated. Only GAGG will later become sensitive.

## 14. Static Geometry Validation

The validator checks the complete 4096-row lattice and 2048-row detector
subset, including total/per-layer/per-bar counts, checkerboard parity,
GAGG depth relation, canonical IDs, coordinates, mother containment,
lateral gaps, touching depth faces, duplicate locations, family membership,
family-local indices, family starts/repeat spacing, macro command content,
explicit no-autocenter encoding for all eight cubic arrays, reconstructed
GATE first-copy placements matched against all 4096 lattice-map rows,
mother containment of every reconstructed copy, absence of legacy geometry
terms, material mapping, and volume sanity.

The result means that the generated artifacts statically describe the
intended geometry. It does not mean GATE has instantiated them.

## 15. Geometry Volume Sanity Checks

```text
single material segment       = 2*2*2 = 8 mm^3
total GAGG volume             = 2048*8 = 16384 mm^3 = 16.384 cm^3
total K9 segment volume       = 2048*8 = 16384 mm^3 = 16.384 cm^3
all explicit material volume  = 32768 mm^3
mother volume                 = 67.2*67.2*32 = 144506.88 mm^3
remaining nominal Air volume  = 144506.88 - 32768 = 111738.88 mm^3
```

The remaining nominal Air volume includes the lateral gaps and the outer
edge margins inside the mother.

## 16. What Step 3 Does NOT Prove

- actual GATE copy ordering;
- actual `volumeID` positions;
- sensitive-detector functionality;
- system hierarchy compatibility;
- runtime overlap detection;
- physics correctness or material attenuation;
- source response or detector efficiency;
- system matrix, paper sensitivity, or reconstruction behavior.

## 17. Step-4 Handoff

Step 4 must runtime-check:

1. GATE parses `magiccube_geometry.mac`.
2. `magicCubeMother` is created with the intended dimensions and material.
3. All eight families instantiate.
4. The expected 512 copies per family occur.
5. 2048 GAGG and 2048 K9 copies are realized.
6. No GATE geometry overlap errors occur.
7. Actual GATE replica/copy/hierarchy IDs are observed.
8. Runtime IDs are mapped to canonical detector IDs.
9. The four `mc_gagg_*` families can be attached as sensitive detectors.
10. Required ROOT hierarchy fields are exposed.

## 18. Change-Control

Future geometry changes must originate from `magiccube_v1_config.json` and
regenerate the macro and maps. Do not hand-edit generated artifacts. Any
change to dimensions, pitch, parity, family decomposition, coordinate
convention, or canonical detector indexing must be deliberate and must
preserve/update the frozen Step-1 and Step-2 contracts before runtime work.
