# Frozen OneCube specification

This document records the single validation configuration. The JSON file at
config/onecube_config.json is the machine-readable source of truth.

## Detector

| Field | Frozen value |
| --- | --- |
| Count | 1 |
| Detector ID | 0 |
| Volume | onecube_crystal |
| Material | GAGG |
| Dimensions | 2 x 2 x 2 mm |
| Center | (0, 0, 0) mm |
| Sensitive | Yes |
| Other detector elements | None |
| K9, BaSO4, SiPM, electronics | None |
| Repeaters/arrays | None |
| Mechanical collimator/plate | None |

The source-facing face is at z = -1 mm. The source is at z = -51 mm,
so the surface distance is exactly 50 mm.

## Source and acquisition

| Field | Frozen value |
| --- | --- |
| Source count / ID | 1 / 0 |
| Particle | gamma |
| Energy | 140 keV monoenergetic |
| Position | (0, 0, -51) mm |
| Position type | Point |
| Angular distribution | Isotropic |
| Activity | 0.0001 Ci = 3.7e6 Bq |
| Start / stop / duration | 0 s / 1 s / 1 s |
| Time slice | 1 s |
| Random engine | MersenneTwister |

## Physics and digitizer

PhotoElectric with StandardModel is enabled. Compton, Rayleigh, and
optical transport are disabled. Gamma, electron, and positron production
cuts remain 1.0 cm, matching the active original-mcsim validation behavior.

The only digitizer chain is the onecube_crystal Singles chain:

~~~
adder -> energyResolution -> spatialResolution -> energyFraming
~~~

The energy resolution is 0.10 FWHM at 140 keV. Spatial resolution is
1.0 mm FWHM with confineInsideOfSmallestElement = true. The accepted energy
window is 120-160 keV.

## Output and matrix

GATE writes ROOT Tree Hits and the shared Singles collection below
runtime/sim/. The merge stage produces runtime/merged/hits.root and
runtime/merged/singles.root.

The PPDF has one row:

~~~
p_00 = n_00 / n_00 = 1.0, when n_00 > 0
~~~

The dense matrix has shape (1, 1). Its .npy value is explicitly
response_per_Bq_s = raw_singles_count / (acquisition_s * activity_Bq),
with units counts/(s*Bq), numerically cps/Bq. The long-form products retain
the raw Singles count and also report cps/MBq.

## Parameter provenance

### ORIGINAL-MCSIM-DERIVED parameters

- Gate material database is copied byte-for-byte from the active original
  repository.
- cylindricalPET system registration and ordinary attachCrystalSD are
  retained.
- PhotoElectric/StandardModel process selection and 1.0 cm production cuts
  are retained.
- Singles digitizer module order and parameters are retained.
- ROOT Tree output, merge boundary, and staged orchestration are retained.
- UB CCR module setup and the explicit project Python interpreter are retained.

### ONECUBE VALIDATION simplifications

- One detector volume and one source position.
- No plate, tungsten, K9, checkerboard, repeaters, arrays, SiPM, electronics,
  optical transport, coincidence, dead time, or pile-up.
- A centered point source replaces the old source geometry and rotation logic.
- The system matrix is intentionally 1 x 1 and ends the milestone; no
  reconstruction is included.
