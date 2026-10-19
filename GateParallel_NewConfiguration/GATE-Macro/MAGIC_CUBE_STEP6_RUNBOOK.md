# Magic-Cube Step-6 Runbook

This is a static-preparation runbook only. Step 6 creates the faithful source,
output, and main-macro port without running GATE or Slurm.

The first Step-7 attempt, job `26105689`, stopped during source parsing with
GATE 9.4 reporting that `gps/rot1` was not a command. The bounded correction
uses `gps/pos/rot1` and `gps/pos/rot2`, and applies the same rigid frame to
`gps/ang/rot1` and `gps/ang/rot2`; all source values and angular limits remain
unchanged. The corrected source hash is
`1b6d5404799163f6a16b6c90d4a3beae2f0c5f19694ed89804b78fa5071a6e25`.

## Files created

- `magiccube_production_source.mac`
- `magiccube_production_output.mac`
- `magiccube_production_main.mac`
- `validate_magiccube_step6_preparation.py`
- `MAGIC_CUBE_STEP6_SOURCE_OUTPUT_MAIN_PORT.md`
- `MAGIC_CUBE_STEP6_RUNBOOK.md`

## Source transformation

The original detector/source axis is x: the original panel is at positive x
and the active source plane is centred at negative x. The Magic-Cube source
convention is negative z. The production source uses the rigid mapping
`(x_orig, y_orig, z_orig) -> (-z_magic, y_magic, x_magic)`, mapping the source
centre to `(0, 0, -187.5) mm`. All source statistics and angular commands are
unchanged.

## Output collections

The active ROOT Tree and Hits output mechanism is retained. Four production
Singles collections are requested:

- `Singles_mc_gagg_ee`
- `Singles_mc_gagg_eo`
- `Singles_mc_gagg_oe`
- `Singles_mc_gagg_oo`

No custom detector-ID output is introduced. The identity policy remains
`POSITION_DERIVED_REQUIRED`; Step 7 must inspect actual output branches.

## Main macro

`magiccube_production_main.mac` preserves the active order: material database,
production geometry, production system, production physics, initialize,
production digitizer, production source, MersenneTwister and 15-second
acquisition, original verbosity, production output, and `startDAQ`. The
original physical tungsten plate is intentionally omitted because the frozen
Magic-Cube detector replaces that physical architecture.

## Static validation

Run the following from the Step-6 working directory:

```bash
python validate_magiccube_step6_preparation.py
```

The expected result is `STATIC STEP-6 PREPARATION: PASS`, including a match
between all eight current frozen-file hashes and the Step-5 closure manifest.

Do not run `magiccube_production_main.mac` until the Step-7 bounded runtime
harness is prepared. Do not submit Slurm or begin parallel/PPDF/system-matrix
work in Step 6.
