# OneCube

OneCube is the smallest complete original-mcsim-style reference pipeline:

~~~
one GAGG cube -> GATE -> Hits/Singles ROOT -> hadd merge
-> PPDF -> 1x1 system matrix -> plots -> final validation
~~~

The detector is one sensitive 2 mm x 2 mm x 2 mm GAGG(Ce) cube at the
origin. The single isotropic 140 keV point source is at (0, 0, -51) mm,
50 mm from the detector's source-facing surface.

This project exists to freeze a working software/data architecture before
detector geometry is expanded. It is not the final full Magic-Cube detector,
and it does not claim full-array sensitivity, resolution, self-collimation,
2048-channel mapping, or reconstruction validation.

All runtime data, logs, plots, and validation products remain below this
OneCube/ directory. Codex prepares the files and static checks; the user
runs the Gate and Slurm commands in ONECUBE_RUNBOOK.md.

The next scaling step should change detector and source cardinality in the
configuration and post-processing tables while preserving the same stage
boundaries and file contracts.
