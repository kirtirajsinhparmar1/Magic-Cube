# Magic-Cube Visualization Runbook

This is a manual, read-only visualization export. It wraps the already validated
magiccube_geometry.mac and does not change detector geometry, materials,
indexing, physics, or Step-4 runtime implementation.

The installed Geant4 11.2.1 tree contains VRML2FILE examples, and the existing
visual.mac also documents the driver. With /vis/open VRML2FILE and no explicit
filename, Geant4 is expected to create a raw file such as g4_00.wrl. The job
renames the two raw exports deterministically after each successful GATE exit.

## 1. Prepare and submit

Run these commands from the GATE-Macro directory:

    cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"

    python validate_magiccube_visualization_preparation.py

    sbatch magiccube_visualization_job.sh

Replace JOB_ID below with the ID printed by sbatch:

    squeue -j <JOB_ID>

## 2. Inspect logs after completion

    sed -n '1,240p' "magiccube_visualization_<JOB_ID>.out"
    sed -n '1,240p' "magiccube_visualization_<JOB_ID>.err"

Inspect the dedicated output directory:

    ls -lh "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/visualization"

The expected final files are:

    magiccube_full.wrl
    magiccube_gagg_only.wrl

The output directory also contains copied macro/material inputs needed for the
relative /control/execute and material-database references. The job removes
only old visualization-generated g4_*.wrl and the two deterministic final
filenames inside that dedicated directory.

## 3. Download for local inspection

After the job completes, download magiccube_full.wrl and
magiccube_gagg_only.wrl to macOS using the institution's SCP workflow or
Open OnDemand file browser. Open the files in a local VRML-compatible viewer.
The full view uses red GAGG and blue K9; the GAGG-only view hides all K9
families so the active self-collimating architecture is easier to inspect.

Do not run GATE, submit another job, or begin Step 5 as part of local viewing.

