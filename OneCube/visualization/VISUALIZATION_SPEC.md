# OneCube visualization specification

## Frozen scientific setup

All scientific values below are read from the existing
`../config/onecube_config.json`; visualization scripts do not maintain a
second detector/source configuration.

| Quantity | Frozen value |
| --- | --- |
| Sensitive detector count | 1 |
| Canonical detector ID | 0 |
| Detector material | GAGG |
| Detector dimensions | 2 x 2 x 2 mm |
| Detector center | `(0, 0, 0)` mm |
| Source count / ID | 1 / 0 |
| Particle | gamma |
| Energy | 140 keV |
| Source center | `(0, 0, -51)` mm |
| Source-to-cube-surface distance | 50 mm |
| Direction convention | negative z is source-facing; source-to-detector direction is +z |
| Activity | 3.7e6 Bq |
| Acquisition | 0 to 1 s, duration 1 s |
| PPDF shape | 1 detector x 1 source |
| System matrix shape | 1 x 1 |

## Exact versus derived content

Exact ROOT-backed views use the actual branch values. In the current products:

- Hits positions use `posX`, `posY`, and `posZ`.
- Hits deposited energy uses `edep` when present.
- Hits time uses `time` when present.
- Singles positions use `globalPosX`, `globalPosY`, and `globalPosZ` when present.
- Singles energy uses `energy` and Singles time uses `time` when present.
- ROOT tree name and branch names are discovered rather than assumed.

Derived views are explicitly labeled as aggregations:

- XY/XZ/YZ projections aggregate exact Hit coordinates.
- Cube intensity is an 8 x 8 x 8 voxel aggregation, weighted by finite
  nonnegative `edep` when available and otherwise by unit Hit occupancy.
- Event-count histograms aggregate exact event IDs into Hits-per-event counts.
- The response dashboard reads the existing PPDF and system-matrix products;
  it does not replace their definitions.

## Detector identity

Native GATE `volumeID[...]` fields are not interpreted as the canonical
detector identity. Because the OneCube contract has one sensitive collection,
visualization metadata assigns detector ID 0 to every accepted Hits/Singles
entry.

## Animation truth contract

The animation, if the local Matplotlib/Pillow writer is available, is a
cumulative Hit buildup. It is ordered by the measured `time` branch when that
branch is finite; otherwise it uses ROOT entry order and says so in
`runtime/animation_status.json`. It does not draw or imply photon trajectories.

If position/time data cannot support a truthful buildup, the animation script
writes an explicit unavailable status instead of fabricating motion.

## Output contract

Static figures are written to `outputs/`. Machine-readable availability and
validation records are written to `runtime/`. The final generated report is
`outputs/VISUALIZATION_REPORT.md`.

The package intentionally has no visualization-only GATE macro or Slurm job:
the requested views are fully supported by the existing OneCube outputs, and
adding a second runtime would risk changing the scientific setup.
