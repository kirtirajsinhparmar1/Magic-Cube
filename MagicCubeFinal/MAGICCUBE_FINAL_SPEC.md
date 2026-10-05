# MagicCubeFinal frozen specification

## Detector and identity

- Block: 67.2 x 67.2 x 32.0 mm, centered at the origin; source-facing surface z=-16 mm.
- Lattice: 16 x 16 x 16; 2 mm cubes; pitches x/y/z = 4.2/4.2/2.0 mm.
- Material: GAGG when `(ix+iy+k)%2==0`, otherwise `K9_V1_PROXY`; 2048 of each.
- Sensitive elements: GAGG only. `detector_id=d*256+iy*16+ix`, with `k=2*d+((ix+iy)%2)`, produces IDs 0..2047.
- Canonical identity is position-derived from `config/detector_map.csv`. Native GATE hierarchy/volume fields are evidence only.

## Source

Validation source 0 is a 140 keV isotropic GPS point at (0,0,-66) mm, activity 3.7e6 Bq, acquisition 1 s. This is 50 mm from the z=-16 mm detector face. The reported nominal 0.7 mm source size is metadata; finite source shape remains open. The full grid is configuration-driven and never fixes the number of sources in code.

## System, physics, and digitizer

The Air-only hierarchy is world -> cylindricalPET -> panel -> module -> block -> Magic-Cube mother. Four GAGG placement families attach with ordinary `attachCrystalSD`; K9 is passive. Physics is PhotoElectric with StandardModel, no Compton/Rayleigh/optical transport, and 1 cm gamma/electron/positron cuts in GAGG regions.

Each GAGG family uses Adder -> EnergyResolution (FWHM 0.10 at 140 keV) -> SpatialResolution (FWHM 1 mm, confined inside the smallest element) -> EnergyFraming (120-160 keV).

This physics configuration preserves the currently validated original-mcsim-style model and may be revisited during final scientific validation against the paper.
