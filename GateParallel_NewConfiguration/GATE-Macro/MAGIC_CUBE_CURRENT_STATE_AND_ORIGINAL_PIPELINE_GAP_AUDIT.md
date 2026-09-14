# Magic-Cube Current State and Original Pipeline Gap Audit

## 1. Executive Summary

The active original workflow is a GATE/Geant4 Monte Carlo pipeline. Its
verified top-level entry point is par_all.sh in
GateParallel_NewConfiguration/GATE-Macro. The production chain submits a
Slurm simulation array, merges GATE ROOT collections with hadd, generates
PPDF data, generates per-run system-matrix data, merges the system-matrix
Parquet files, and produces plots.

The original GATE entry macro is SPEBT.mac. Its active control/execute order
is geometry.mac, plate.mac, system.mac, physics.mac, GATE initialization,
digitizer.mac, source.mac, verbose.mac, output.mac, and acquisition. The
original active physics selection is PhotoElectric with StandardModel;
Compton and Rayleigh scattering are commented out. The original digitizer
chain is Adder, energy resolution, spatial resolution, and energy framing,
with 10 percent FWHM at 140 keV, 1 mm FWHM spatial resolution, and a
120–160 keV energy window. The active source is a 140 keV gamma GPS plane
source. The output contains GATE Hits and Singles ROOT collections.

Magic-Cube Steps 1–4 are complete as a specification, material/geometry
implementation, static geometry validation, and real-GATE raw-Hits runtime
validation. The runtime identity result is
POSITION_DERIVED_REQUIRED: a hit position must be mapped through
detector_map.csv to obtain canonical detector IDs 0–2047. These completed
pieces do not yet constitute a production replacement for the original
digitizer, source, output, launcher, PPDF, system-matrix, or plotting chain.

The immediate next implementation component is the original-style
digitizer. It should port digitizer.mac with the original module order and
parameters, attach the equivalent chain to the four active Magic-Cube GAGG
families, and integrate with a future production main macro. It must not
introduce new physics or detector-response methodology.

## 2. Project Rule: Faithful Original-Pipeline Port

The project objective is a faithful port of the original active repository
pipeline to the Ref. 29 Magic-Cube detector. The original workflow,
physics approach, digitizer philosophy, source/output workflow,
parallelization pattern, PPDF processing concept, and system-matrix
processing logic are to remain unchanged unless the detector change makes a
specific adaptation necessary.

The Magic-Cube-specific changes proven necessary by the repository are the
replacement of the original detector geometry, the use of four active GAGG
family volumes rather than the original xlayer hierarchy, the
attachCrystalSDnoSystem sensitive-detector realization, and position-based
canonical detector mapping. A methodological redesign is outside this
audit.

No Compton study, Rayleigh study, attenuation experiment, production-cut
convergence study, new detector-response model, new system-matrix
formulation, Gate run, Slurm submission, production pipeline, system-matrix
generation, or reconstruction was performed.

## 3. Repository Layout Relevant to the Active Pipeline

The active original files are concentrated in:

    /vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro

Relevant active original files are:

| Classification | Files | Role |
|---|---|---|
| GATE main macro | SPEBT.mac | Main control/execute sequence |
| GATE component macros | geometry.mac, plate.mac, system.mac, physics.mac, digitizer.mac, source.mac, output.mac | Geometry, plate, system, physics, digitizer, source, and output |
| Shell/Slurm orchestration | par_all.sh, par_vscratch.sh, par_hadd.sh, par_ppdf.sh, ppdf.sh, par_sysmat.sh, sysmat.sh, par_mergesysmat.sh, par_sysmatplot.sh | Active simulation and downstream jobs |
| Active merge/plot helpers | merge_source_positions.sh, merge_detector_positions.sh, merge_ppdf.sh, merge_highlighted_detector.sh, plot_positions.sh | Active submitted auxiliary data/plot stages |
| Active Python processing | generate_ppdf_with_detectors.py, generate_sysmat.py, merge_source_positions.py, merge_detector_positions.py, merge_ppdf.py, merge_highlighted_detector.py, plot_positions.py | PPDF, system matrix, merging, and plotting |
| Analytical or alternate code | get_all_ppdfs_mpi_optimized.py, generate_ppdf.py, par_sysmatbin.sh, par_sysmatplotbinned.sh, par_sysmatplotconsist.sh, merge_and_plot.py, older launchers and notebooks | Not invoked by par_all.sh |
| Magic-Cube reusable material/geometry | MAGIC_CUBE_V1_SPEC.md, MAGIC_CUBE_V1_MATERIALS.md, MAGIC_CUBE_V1_GEOMETRY.md, magiccube_v1_config.json, generate_magiccube_geometry.py, magiccube_geometry.mac, magiccube_lattice_map.csv, detector_map.csv, validate_magiccube_geometry.py | Frozen V1 contract, generated geometry/maps, and static validation |
| Magic-Cube Step-4 diagnostics | magiccube_runtime_geometry_check.mac, magiccube_runtime_system.mac, magiccube_runtime_physics.mac, run_magiccube_step4_runtime.py, inspect_magiccube_runtime.py, validate_magiccube_runtime.py, validate_magiccube_step4_preparation.py, magiccube_step4_job.sh | Diagnostic runtime harness and validators |
| Step-4 evidence | MAGIC_CUBE_STEP4_CLOSURE_AUDIT.md, MAGIC_CUBE_V1_RUNTIME_VALIDATION.md | Closure report and older/superseded runtime note |

The active chain was identified by direct submission calls in par_all.sh.
The presence of a script in the directory was not treated as evidence that
the script is active.

## 4. Original Active Pipeline — End-to-End Execution Chain

The verified production chain is:

    par_all.sh
      -> sbatch par_vscratch.sh
      -> Slurm simulation array 0–100
      -> per-task SPEBT_$SLURM_ARRAY_TASK_ID.mac and output_$SLURM_ARRAY_TASK_ID.mac
      -> Gate
      -> SPEBT_$SLURM_ARRAY_TASK_ID.hits_*.root and SPEBT_$SLURM_ARRAY_TASK_ID.Singles_*.root
      -> par_hadd.sh, array 1–100
      -> hits$SLURM_ARRAY_TASK_ID.root and singles$SLURM_ARRAY_TASK_ID.root
      -> par_ppdf.sh -> ppdf.sh -> generate_ppdf_with_detectors.py
      -> ppdf_*.parquet and related source/detector Parquet files
      -> par_sysmat.sh -> sysmat.sh -> generate_sysmat.py
      -> system_matrix_*.parquet
      -> par_mergesysmat.sh
      -> combined_system_matrix.parquet
      -> par_sysmatplot.sh
      -> System Matrix Plots/PPDF_Detector_$detector_id.png

In parallel with the PPDF branch, par_all.sh submits the source-position,
detector-position, PPDF, and highlighted-detector merge/plot helpers. The
directly submitted auxiliary chain is:

    merge_source_positions.sh
    merge_detector_positions.sh
    merge_ppdf.sh
    merge_highlighted_detector.sh
    plot_positions.sh

The simulation-to-hadd-to-PPDF and simulation-to-system-matrix dependencies
are submitted by par_all.sh with Slurm afterok dependencies. The exact
submission order and variable handling in that script are part of the
original behavior. In particular, par_all.sh reassigns the ppdf_job
variable when it submits merge_ppdf.sh, and the highlighted-detector merge
is then dependent on that reassigned job identifier. This is documented as
an inherited orchestration risk, not changed here.

The task indexing is not uniform: par_vscratch.sh runs array indices 0–100,
whereas par_hadd.sh, par_ppdf.sh, and par_sysmat.sh run indices 1–100.
Therefore the downstream chain does not process simulation task 0 under its
normal array ranges.

The active per-task shell path is:

    par_vscratch.sh
      -> copy output.mac and replace the array placeholder
      -> copy SPEBT.mac and point it to the copied output macro
      -> Gate SPEBT_$SLURM_ARRAY_TASK_ID.mac

The active downstream shell paths are:

    par_hadd.sh -> hadd
    par_ppdf.sh -> ppdf.sh -> generate_ppdf_with_detectors.py
    par_sysmat.sh -> sysmat.sh -> generate_sysmat.py
    par_mergesysmat.sh -> Parquet concat -> combined_system_matrix.parquet
    par_sysmatplot.sh -> detector-specific heatmap PNGs

## 5. Original Main GATE Macro

SPEBT.mac is the active main macro. Its functional execution order is:

1. Set the material database to GateMaterials.db.
2. Execute geometry.mac.
3. Execute plate.mac.
4. Execute system.mac.
5. Execute physics.mac.
6. Initialize the GATE run.
7. Execute digitizer.mac.
8. Execute source.mac.
9. Set the random engine to MersenneTwister.
10. Set application time start to 0 s and stop to 15 s.
11. Execute verbose.mac.
12. Execute output.mac.
13. Start the DAQ.

The visualization, time-slice, and alternative source controls visible in
the file are commented out. Geometry, plate, system, and physics must be
defined before initialization. Digitizer, source, and output are configured
after initialization in this repository's active macro order and before
startDAQ.

The current Magic-Cube runtime files are not included by SPEBT.mac. The
Magic-Cube therefore does not yet have a production main macro that
reproduces this sequence with its own geometry, system attachment, physics,
digitizer, source, and output.

## 6. Original Detector Geometry and System

The original geometry is a conventional GATE cylindricalPET hierarchy, not
the Magic-Cube.

The world is a 300 x 300 x 300 mm box. A cylindricalPET system is centered
at the origin with outer radius 150 mm, inner radius 100 mm, height 200 mm,
and Air material. A panel is a 100 x 108 x 20 mm box at x = 137 mm. Inside
it, the hierarchy includes:

| Level or volume | Dimensions / behavior |
|---|---|
| panel | 100 x 108 x 20 mm box |
| module | 97 x 108 x 20 mm box |
| block | 27 x 108 x 20 mm box |
| zlayer | 27 x 108 x 3 mm box |
| xlayer1–xlayer8 prototypes | 3 x 3 x 3 mm GAGG crystals |

The panel, module, block, and zlayer use one-repeat linear structures. The
first seven xlayer prototypes repeat 16 times along y with a 6.72 mm
vector. xlayer8 repeats 32 times along y with a 3.36 mm vector. This gives
7 x 16 + 32 = 144 GAGG crystal placements. The xlayer prototype x
translations are:

| Volume | x | y | z |
|---|---:|---:|---:|
| xlayer1 | -12 | 0.18 | 0 |
| xlayer2 | -9 | 0.81 | 0 |
| xlayer3 | -6 | -0.45 | 0 |
| xlayer4 | -3 | 1.23 | 0 |
| xlayer5 | 0 | -0.87 | 0 |
| xlayer6 | 3 | 1.65 | 0 |
| xlayer7 | 6 | -1.29 | 0 |
| xlayer8 | 9 | 0.18 | 0 |

plate.mac adds a tungsten MetalPlate below module. The plate is a
2 x 107.52 x 20 mm box translated to x = -44 mm. An Air hole is a
2 x 2 x 2 mm box repeated as an 1 x 11 x 10 cubic array with vectors
0, 10, 2 mm.

system.mac defines the cylindricalPET/rsector/module/submodule/crystal
hierarchy and attaches CrystalSD to xlayer1 through xlayer8. The active
CrystalSD attachments are the xlayer volumes; the layer1–layer8
attachments are commented. The system macro does not assign the
Magic-Cube canonical detector IDs. The downstream Python code instead
assumes particular GATE volumeID fields.

The original geometry assumptions that matter to the downstream code are:

- There are 144 active GAGG crystal channels.
- xlayer names and their conventional system hierarchy exist.
- volumeID[2] can be selected as 0.
- volumeID[6] identifies a detector channel in the range 0–143.

## 7. Original Physics

physics.mac activates:

    /gate/physics/addProcess PhotoElectric
    /gate/physics/Gamma/PhotoElectric/SetModel StandardModel
    /gate/physics/processList Enabled
    /gate/physics/processList Initialized

The active process selection is therefore PhotoElectric-only with the
StandardModel for PhotoElectric.

The following processes are present only as commented or disabled commands
in the active file:

- Compton
- RayleighScattering, including the commented Penelope model command
- ElectronIonisation
- Bremsstrahlung
- PositronAnnihilation
- MultipleScattering for electrons and positrons

The active file sets Gamma, Electron, and Positron cuts in the xlayer1
through xlayer8 regions to 1.0 cm. Phantom cuts and a maximum-step setting
are commented out.

No physics change is required by this audit. The Magic-Cube diagnostic
physics macro also selects PhotoElectric with StandardModel and does not
enable Compton or Rayleigh. At the process-selection level, the Step-4
baseline already matches the original PhotoElectric-only approach. Full
physics-file equivalence is not complete because the diagnostic macro does
not reproduce the original xlayer-specific 1.0 cm cuts and is not wired
through a production Magic-Cube main macro.

## 8. Original Digitizer

digitizer.mac defines eight analogous chains, one for each xlayer. Each
chain has this exact module order:

    Adder
      -> energyResolution
      -> spatialResolution
      -> energyFraming

The active values are:

| Module | Parameter | Value |
|---|---|---|
| energy resolution | FWHM | 0.10 |
| energy resolution | reference energy | 140 keV |
| spatial resolution | FWHM | 1.0 mm |
| spatial resolution | confinement | confineInsideOfSmallestElement true |
| spatial resolution | verbosity | 0 |
| energy framing | minimum | 120 keV |
| energy framing | maximum | 160 keV |

No active pileup, deadtime, efficiency, or alternative readout module was
found in digitizer.mac. The active digitizer is therefore a simple
per-layer Adder-to-resolution-to-window chain.

The values and module order are original behavior to preserve. The
Magic-Cube adaptation is the collection/hierarchy association: the
xlayer-specific chain names must be translated to the active Magic-Cube
GAGG family collections. The four K9 families remain passive and must not
become digitizer channels merely because they are geometrically placed.

## 9. Original Source

source.mac has an older cylinder source block commented out. The active
source is source1 with:

| Source property | Active value |
|---|---|
| particle | gamma |
| energy | Mono 140.0 keV |
| activity | 0.0001 Ci |
| source type | GPS plane |
| plane center | -187.5, 0, 0 mm |
| plane half-widths | halfx 250 mm, halfy 250 mm |
| angular type | iso |
| theta | min = max = 90 degrees |
| phi | 150–210 degrees |
| acquisition | application time 0–15 s |

The source file does not configure an explicit event count or explicit
random seed. The active pipeline therefore uses activity/time behavior, not
a fixed source-event loop.

This audit does not substitute the future Magic-Cube source contract from
MAGIC_CUBE_V1_SPEC.md. The future Tc-99m, source-plane, field-of-view,
sampling, and energy-window statements in that specification are recorded
as future contracts, not as an implemented production source.

## 10. Original Output / ROOT Structure

output.mac enables the ROOT tree and adds the output filename:

    /vscratch/grp-rutaoyao/Tridev/SPEBT_$SLURM_ARRAY_TASK_ID.root

It enables Hits and adds the Singles collection. The active output file
therefore produces GATE ROOT data containing Hits and Singles collections.
The per-collection files are later consumed by the hadd patterns:

    SPEBT_$SLURM_ARRAY_TASK_ID.hits_*.root
    SPEBT_$SLURM_ARRAY_TASK_ID.Singles_*.root

The output.mac branch parameter-name commands are commented rather than
active. They document expected fields including hit posX, posY, volumeID[2],
volumeID[6], and eventID, plus Singles sourcePosX, sourcePosY, sourcePosZ,
and eventID. The downstream Python scripts directly require those branches,
so those fields are proven as downstream input requirements even though the
parameter-name commands are not active output commands.

No Magic-Cube production output macro exists. The Step-4 runner uses raw
Hits only and is diagnostic output, not an equivalent of the original
Hits/Singles production output.

## 11. Original Slurm and Parallel Workflow

par_all.sh is the active orchestration entry point. It submits:

1. par_vscratch.sh for the simulation array.
2. par_hadd.sh after simulation success.
3. par_ppdf.sh after the merge stage.
4. source-position, detector-position, PPDF, and highlighted-detector
   merge helpers.
5. plot_positions.sh after the relevant auxiliary merge jobs.
6. par_sysmat.sh, par_mergesysmat.sh, and par_sysmatplot.sh for the system
   matrix branch.

par_vscratch.sh requests:

- array 0–100;
- one task and four CPUs per task;
- 25,000 MB memory;
- 10 hours;
- the general-compute partition and matching QoS;
- the cluster GATE 9.4 module environment.

It changes to the original working directory
/user/tridevme/Tridev_SPEBT/GateParallel_NewConfiguration/GATE-Macro,
copies output.mac into an array-specific output macro, replaces the
SLURM-array placeholder, copies SPEBT.mac into an array-specific main
macro, points that main macro to the copied output macro, and invokes Gate.
The output directory is /vscratch/grp-rutaoyao/Tridev.

par_hadd.sh, par_ppdf.sh, and par_sysmat.sh use arrays 1–100. Each reads
the array task identifier to construct its per-run filenames. par_ppdf.sh
and par_sysmat.sh are wrappers around ppdf.sh and sysmat.sh respectively.

The active scripts do not set a per-task seed. The original array and
dependency behavior, including the 0-versus-1 indexing mismatch, is part
of the current-state record and was not corrected.

## 12. Original ROOT Merge Stage

par_hadd.sh changes to /vscratch/grp-rutaoyao/Tridev and, for each
downstream array task, executes:

    hadd hits$SLURM_ARRAY_TASK_ID.root SPEBT_$SLURM_ARRAY_TASK_ID.hits_*.root
    hadd singles$SLURM_ARRAY_TASK_ID.root SPEBT_$SLURM_ARRAY_TASK_ID.Singles_*.root

Hits and Singles are merged separately before the active PPDF and
system-matrix scripts run. The file naming preserves the task/run
partition, but the downstream Python scripts match Hits and Singles by
eventID only.

The later system-matrix merge is not a ROOT merge. par_mergesysmat.sh
globs system_matrix_*.parquet, reads every matching file, concatenates
the data frames with ignore_index true, and writes
/vscratch/grp-rutaoyao/Tridev/combined_system_matrix.parquet. It does not
deduplicate or aggregate rows.

The auxiliary source, detector, PPDF, and highlighted-detector merge
scripts concatenate Parquet files and drop duplicate rows before writing
their merged outputs. Those are separate from the ROOT hadd stage.

## 13. Original PPDF Pipeline

The active PPDF path is:

    par_ppdf.sh
      -> ppdf.sh
      -> generate_ppdf_with_detectors.py

The Python script receives a Hits filename and a Singles filename. It
opens both from /vscratch/grp-rutaoyao/Tridev using tree;1. It requires:

- Hits posX, posY, volumeID[2], volumeID[6], eventID;
- Singles sourcePosX, sourcePosY, sourcePosZ, eventID.

Its active algorithm is:

1. Select volumeID[2] equal to 0.
2. Iterate over volumeID[6] values 0–143 to construct highlighted detector
   position data.
3. Reset the selected detector to volumeID[6] equal to 0 for the PPDF
   selection.
4. Select Hits with volumeID[2] = 0 and volumeID[6] = 0.
5. Keep Singles rows whose eventID occurs in the selected Hits.
6. Group the matched Singles by sourcePosX and sourcePosY.
7. Count rows in each source-position group.
8. Normalize each count by the sum of counts for the selected detector.

The active normalized quantity is therefore:

    normalized_count(i) = count(i) / sum over i of count(i)

for the selected detector volumeID[6] = 0. sourcePosZ is read but is not
part of the grouping key. Energy, deposited energy, source ID, and run ID
are not used by this algorithm.

The script writes PPDF, source-position, detector-position,
selected-detector-position, and highlighted-detector Parquet files under
the Tridev output directory. The highlighted loop does not make the PPDF
itself a 144-detector result: the PPDF selection is reset to detector 0.

The active PPDF implementation has no fixed Magic-Cube 2048 detector map,
no position-to-detector identity conversion, and no fixed source-grid
dimensions proven by the code. Empty matching selections are not handled
with an explicit error path before normalization, which is a possible
runtime failure mode.

## 14. Original System-Matrix Pipeline

The active system-matrix path is:

    par_sysmat.sh
      -> sysmat.sh
      -> generate_sysmat.py
      -> system_matrix_*.parquet, named from each input Hits basename
      -> par_mergesysmat.sh
      -> combined_system_matrix.parquet

generate_sysmat.py requires the same Hits and Singles fields as the active
PPDF script. For each detector_id in range 144 it:

1. Selects Hits with volumeID[2] = 0 and volumeID[6] = detector_id.
2. Matches Singles by eventID membership.
3. Groups matched Singles by sourcePosX and sourcePosY.
4. Counts rows in each source-position group.
5. Normalizes the counts separately for that detector.
6. Adds detector_id and concatenates the detector data.
7. Writes a long-form Parquet data frame.

For detector j and source-position group i, the implemented values are:

    count(j,i) = number of matched Singles rows for detector j in group i

    normalized_count(j,i) =
        count(j,i) / sum over i of count(j,i)

The implementation retains both count and normalized_count columns, but
the normalized quantity is detector-wise normalized response. It does not
write a fixed dense 2048-by-source-grid matrix. The source dimension is the
set of source-position groups present in the input, so a fixed source-grid
shape is UNKNOWN / NOT PROVEN FROM THE REPOSITORY.

The implementation uses eventID as the only event-matching key. It does not
use runID, sourceID, energy, deposited energy, or a separate event/run
composite key. The selected detector dimension is hardcoded to 144 through
volumeID[6].

par_mergesysmat.sh concatenates all system_matrix_*.parquet files without
deduplication or aggregation. par_sysmatplot.sh filters the combined file
by detector_id, reads detector_id, sourcePosX, and sourcePosY, bins an
unweighted 200 x 200 two-dimensional histogram, normalizes the display
heatmap by its sum, transposes it for display, and writes one PNG per
detector task. The plotting array is 0–143; its comment says 128 jobs,
which is inconsistent with the active range.

The plot script does not use count or normalized_count as histogram
weights. It is therefore a visualization of row occupancy rather than a
direct rendering of the stored response values. This is original behavior
and is documented as a limitation, not corrected.

The frozen Magic-Cube specification contains a future exposure/area-based
matrix contract and explicitly says legacy detector-wise normalization
should not define the future Magic-Cube matrix. No Magic-Cube system-matrix
implementation exists yet. Consequently, the normalization stage is a
decision point: faithful initial porting would preserve the original
normalized_count behavior, while adopting the frozen future contract would
be a later, explicit project decision rather than a detector-forced change.

## 15. Original Detector-ID Assumptions

The original downstream identity logic is not a canonical detector map.
It assumes the conventional GATE hierarchy and fixed volumeID positions:

- volumeID[2] must equal 0;
- volumeID[6] is treated as the detector identifier;
- detector_id ranges from 0 through 143;
- the xlayer CrystalSD hierarchy produces those fields;
- Hits and Singles are matched using eventID;
- source identity is represented by sourcePosX and sourcePosY groups.

The active system macro attaches CrystalSD to xlayer1 through xlayer8,
which is the source of the hierarchy assumed by the Python scripts. No
repository evidence assigns a canonical detector identity independently of
that GATE volumeID layout.

This assumption cannot be retained for Magic-Cube. Step-4 runtime evidence
shows that fixed GATE volumeID components are noncanonical: the observed
volumeID[2] values identify family-related offsets rather than canonical
detector IDs. The canonical Magic-Cube identity must therefore be derived
from hit position and detector_map.csv.

## 16. Original Alternative / Analytical Code

The active production classification is:

| Code | Classification | Evidence |
|---|---|---|
| par_all.sh and its directly submitted chain | ACTIVE | Direct top-level submission calls |
| generate_ppdf_with_detectors.py | ACTIVE | Called by ppdf.sh, which is called by par_ppdf.sh |
| generate_sysmat.py | ACTIVE | Called by sysmat.sh, which is called by par_sysmat.sh |
| get_all_ppdfs_mpi_optimized.py | NOT ACTIVE; analytical/experimental alternative | Uses HDF5, local_functions, pymatcal, and mpi4py; no call from par_all.sh or active wrappers |
| generate_ppdf.py | NOT ACTIVE; legacy single-detector alternative | Not called by the active PPDF wrapper and uses a different fixed volume selection |
| par_sysmatbin.sh and related binned/consistent plotting scripts | NOT ACTIVE; alternate post-processing | No submission from par_all.sh |
| merge_and_plot.py and old launchers/notebooks | HISTORICAL or NOT ACTIVE | No active-chain call |

An analytical alternative exists: YES. It is not active in the production
chain: NO. Its dependency availability is UNKNOWN / NOT PROVEN FROM THE
REPOSITORY and was not tested.

The presence of these alternatives does not change the active methodology.
The active chain is the Gate/Geant4 Monte Carlo path.

## 17. Current Magic-Cube Implementation

### Frozen specification and configuration

MAGIC_CUBE_V1_SPEC.md and magiccube_v1_config.json define:

- magicCubeMother dimensions 67.2 x 67.2 x 32.0 mm, centered at the origin;
- x and y as lateral axes and z as depth;
- source-facing surface at z = -16 mm;
- future nominal source plane at z = -66 mm;
- ix, iy, k each ranging 0–15;
- 2 x 2 x 2 mm segments;
- 4.2 mm lateral pitch and 2.2 mm lateral air gap;
- checkerboard GAGG/K9 assignment using (ix + iy + k) modulo 2;
- 2048 GAGG and 2048 K9 lattice positions;
- canonical detector_id = d*256 + iy*16 + ix for the 2048 GAGG positions;
- lattice map index k*256 + iy*16 + ix.

The future source and future system-matrix statements in the specification
are not active source, output, or matrix implementations.

### Materials

MAGIC_CUBE_V1_MATERIALS.md and GateMaterials.db define GAGG, Air, and the
provisional K9_V1_PROXY. K9_V1_PROXY deliberately copies a Glass-based
definition with density 2.5 and is marked provisional. No optical transport
is part of V1. The GAGG, Air, and proxy material availability is sufficient
for the current V1 geometry/runtime check, but the exact final K9 material
remains unresolved.

### Generated geometry and maps

generate_magiccube_geometry.py deterministically generates:

- magiccube_geometry.mac;
- magiccube_lattice_map.csv;
- detector_map.csv.

The generated macro defines magicCubeMother as an Air box and eight
families:

    mc_gagg_ee
    mc_k9_ee
    mc_gagg_eo
    mc_k9_eo
    mc_gagg_oe
    mc_k9_oe
    mc_gagg_oo
    mc_k9_oo

The actual generated file contains the four GAGG and four K9 family names;
the two odd/even naming dimensions are used to partition the checkerboard.
Each family has 8 x 8 x 8 = 512 placements, for 4096 total placements.
Each crystal is 2 x 2 x 2 mm. The repeater vectors are 8.4, 8.4, and
4.0 mm. The macro explicitly sets cubicArray autoCenter false because each
family translation represents the first-copy center.

The static validator reports 4096 placements, 4096 lattice-map matches,
zero duplicates, zero placements outside the mother, and 2048 positions
in each material class.

### Step-4 runtime

MAGIC_CUBE_STEP4_CLOSURE_AUDIT.md records a successful real-GATE runtime
validation using GATE 9.4 and Geant4 11.2.1. The runtime used:

- four GAGG family attachments with attachCrystalSDnoSystem;
- passive K9 and Air;
- raw Hits only;
- 32 diagnostic probes;
- a separate external 140 keV smoke test.

The closure report records 2592 mapped hits, zero unmapped hits, zero
ambiguous hits, and zero wrong-detector hits across the diagnostic probes,
with the external smoke test also passing. The successful manual Slurm job
was 25779143, as recorded in the closure report; it was not rerun for this
audit.

## 18. Magic-Cube Runtime Identity

The authoritative runtime identity classification is:

    POSITION_DERIVED_REQUIRED

The mapping path is:

    hit position
      -> detector_map.csv
      -> lattice coordinates and canonical detector_id

The canonical detector ID range is 0–2047 and contains only the 2048 GAGG
positions. K9 positions are passive and do not receive active detector IDs.

The Step-4 inspector maps hit positions to detector_map.csv using the
detector segment geometry and checks native GATE IDs separately. The closure
evidence shows that native volumeID components are not safe substitutes for
the canonical IDs. Every future PPDF and system-matrix path must therefore
map hit positions before detector grouping.

## 19. Current Magic-Cube Components: Production vs Diagnostic

| Component | Classification | Current role |
|---|---|---|
| MAGIC_CUBE_V1_SPEC.md | FROZEN PRODUCTION-REUSABLE COMPONENT | Geometry, identity, and future-contract specification |
| magiccube_v1_config.json | FROZEN PRODUCTION-REUSABLE COMPONENT | Generator input for the V1 lattice |
| MAGIC_CUBE_V1_MATERIALS.md | FROZEN V1 MATERIAL CONTRACT | Material intent; K9 remains provisional |
| GateMaterials.db definitions | REQUIRED, PRODUCTION-REUSABLE WITH K9 CAVEAT | GAGG, Air, and K9 proxy definitions |
| generate_magiccube_geometry.py | PRODUCTION-REUSABLE GENERATOR | Deterministic macro/map generation |
| magiccube_geometry.mac | PRODUCTION-REUSABLE GENERATED GEOMETRY | V1 detector geometry fragment; assumes a surrounding world |
| magiccube_lattice_map.csv | PRODUCTION-REUSABLE MAP | Lattice-coordinate mapping |
| detector_map.csv | PRODUCTION-REUSABLE MAP | Canonical GAGG detector identity |
| validate_magiccube_geometry.py | HARMLESS VALIDATION INFRASTRUCTURE | Static placement/material/map checks |
| magiccube_runtime_system.mac | STEP-4 DIAGNOSTIC HARNESS | Proves four GAGG no-system CrystalSD attachments; not wired into production |
| magiccube_runtime_physics.mac | STEP-4 DIAGNOSTIC HARNESS | Proves PhotoElectric baseline; does not reproduce full original cuts/wiring |
| magiccube_runtime_geometry_check.mac | DIAGNOSTIC ONLY | Builds and initializes the geometry without production acquisition |
| run_magiccube_step4_runtime.py | DIAGNOSTIC ONLY | 32 probes and a 140 keV smoke test with raw Hits |
| inspect_magiccube_runtime.py | DIAGNOSTIC ONLY | Position mapping and runtime identity observations |
| validate_magiccube_runtime.py | DIAGNOSTIC ONLY | Validates the Step-4 runtime evidence |
| validate_magiccube_step4_preparation.py | DIAGNOSTIC ONLY | Static preparation/workflow checks |
| magiccube_step4_job.sh | DIAGNOSTIC ONLY | Single Step-4 validation job wrapper |
| Step-4 temporary ROOT/log/JSON/CSV outputs | DIAGNOSTIC ONLY | Runtime evidence, not production imaging output |
| MAGIC_CUBE_V1_RUNTIME_VALIDATION.md | HISTORICAL / SUPERSEDED EVIDENCE | Older runtime note; closure report is authoritative |

The 32 probes, smoke source, raw-Hits output, and Step-4 job are not
production equivalents of the original source/output pipeline. They are
valuable validation infrastructure and should remain available for
regression checks.

## 20. Master Original-vs-Magic-Cube Gap Table

| Pipeline stage | Original active file(s) | Original behavior | Current Magic-Cube file(s) | Current status | Minimum required change | Must original behavior remain? |
|---|---|---|---|---|---|---|
| material database | SPEBT.mac, GateMaterials.db | Loads the original material database for GAGG/geometry | GateMaterials.db, MAGIC_CUBE_V1_MATERIALS.md | COMPLETE — NECESSARY MAGIC-CUBE ADAPTATION | Keep GAGG/Air and provide the V1 K9 proxy or approved final K9 material | Material-loading workflow yes; material definitions must change for the detector |
| geometry | geometry.mac | CylindricalPET, panel/module/block/zlayer, 144 xlayer GAGG crystals | magiccube_geometry.mac, generator, V1 config | COMPLETE — NECESSARY MAGIC-CUBE ADAPTATION | Replace the old hierarchy with 4096 checkerboard placements and retain validated maps | GATE geometry-before-init order yes; old geometry no |
| plate/collimator | plate.mac | Tungsten plate with repeated Air holes | No Magic-Cube plate file | NOT APPLICABLE TO MAGIC-CUBE | Do not carry over the old plate unless a later detector-specific requirement proves it necessary | No; it is part of the old detector geometry |
| system hierarchy | system.mac | cylindricalPET system with panel/module/block/crystal hierarchy | magiccube_runtime_system.mac | PARTIAL — DIAGNOSTIC IMPLEMENTATION ONLY | Put the four GAGG attachCrystalSDnoSystem commands into the production macro sequence | Sensitive-detector setup before acquisition yes; old hierarchy no |
| sensitive detector | system.mac | CrystalSD attached to xlayer1–xlayer8 | magiccube_runtime_system.mac, closure report | PARTIAL — DIAGNOSTIC IMPLEMENTATION ONLY | Production-wire the four active GAGG SD attachments and preserve passive K9 | Active GAGG-only readout yes; xlayer names no |
| physics | physics.mac | PhotoElectric StandardModel; other listed processes commented; xlayer cuts 1 cm | magiccube_runtime_physics.mac | PARTIAL — DIAGNOSTIC IMPLEMENTATION ONLY | Reproduce process selection and appropriate cut policy in a production Magic-Cube macro | PhotoElectric-only behavior and disabled Compton/Rayleigh yes |
| digitizer | digitizer.mac | Eight Adder → energy resolution → spatial resolution → framing chains | None | NOT YET PORTED | Port the chain and exact values to the four active GAGG collections | Yes: order, values, window, and no extra modules |
| source | source.mac | 140 keV gamma GPS plane, activity/time acquisition, restricted angular range | None; Step-4 runner is diagnostic | NOT YET PORTED | Port the original active source configuration first | Yes: original source methodology and values |
| ROOT output | output.mac | ROOT tree with Hits and Singles collections | None; Step-4 raw Hits only | NOT YET PORTED | Create production output preserving Hits/Singles fields needed downstream | Yes: Hits/Singles architecture |
| main macro | SPEBT.mac | Executes components in verified order and starts DAQ | None | NOT YET PORTED | Create a Magic-Cube main macro with the same order and adapted component includes | Yes: control/execute order and acquisition flow |
| simulation launcher | par_vscratch.sh | Copies per-task macros, substitutes task IDs, invokes Gate | magiccube_step4_job.sh only | NOT YET PORTED | Create a production launcher using the original copy/substitution/execute pattern | Yes: launcher behavior and resource pattern unless path adaptation requires change |
| Slurm array | par_all.sh, par_vscratch.sh | Simulation array 0–100; downstream arrays 1–100; afterok chain | None | NOT YET PORTED | Adapt paths and production macro names while preserving the original array/dependency pattern | Yes, including known indexing unless later deliberately corrected |
| ROOT merge | par_hadd.sh | Separate hadd of Hits and Singles per task | None | NOT YET PORTED | Reuse the two-collection hadd flow with Magic-Cube output names | Yes |
| PPDF | par_ppdf.sh, ppdf.sh, generate_ppdf_with_detectors.py | EventID matching, selected detector 0, source X/Y grouping, detector-wise normalization | None | NOT YET PORTED | Port the algorithm and replace fixed volumeID selection with position/map detector identity | Concept and normalization yes unless explicitly decided otherwise |
| detector mapping | volumeID[6] in original Python | Fixed 0–143 volumeID detector assumption | detector_map.csv, inspector, closure report | COMPLETE — NECESSARY MAGIC-CUBE ADAPTATION | Use position-to-map conversion in production PPDF/matrix code | Identity must remain deterministic; the mechanism must change |
| system matrix | par_sysmat.sh, sysmat.sh, generate_sysmat.py | Per-detector source-position counts and detector-wise normalized_count | None | NOT YET PORTED | Port the same long-form algorithm for 2048 mapped detectors | Yes for a faithful first port |
| system-matrix normalization | generate_sysmat.py | normalized_count(j,i) = count(j,i) divided by detector-j total | Future contract only in V1 spec | NEEDS DECISION | Decide explicitly whether initial port preserves legacy normalization or adopts the future contract | Original behavior should remain for faithful port until a deliberate decision |
| plotting | par_sysmatplot.sh, plot_positions.py | Per-detector 200 x 200 occupancy heatmaps and auxiliary plots | None | NOT YET PORTED | Adapt detector count, paths, and map identity while preserving original plot behavior | Yes unless a later plotting requirement changes it |

## 21. Required Magic-Cube-Specific Changes

Only the following changes are presently justified by the detector
replacement or by the proven runtime identity behavior:

1. Replace the original cylindricalPET/xlayer/plate detector geometry with
   the 67.2 x 67.2 x 32.0 mm Magic-Cube mother and its 4096 checkerboard
   placements.
2. Keep the four GAGG families active and the four K9 families passive.
3. Attach the sensitive detector with the proven
   attachCrystalSDnoSystem mechanism to the four GAGG family volumes.
4. Replace the original 144-channel volumeID selection with position-based
   mapping through detector_map.csv and canonical IDs 0–2047.
5. Replace downstream loops, collection associations, and detector-shaped
   arrays that are intrinsically tied to 144 channels with the 2048 active
   GAGG channels.
6. Translate the original xlayer-specific digitizer associations to the
   active GAGG family collections while retaining the original digitizer
   modules and values.
7. Omit the old tungsten plate from the Magic-Cube geometry because it is
   not part of the current Magic-Cube detector model; adding or removing
   any further collimation is outside this audit.

The K9_V1_PROXY definition is a V1 material adaptation required to build
the checkerboard model, but it is explicitly provisional. Finalizing K9 is
a material-specification decision, not a reason to redesign the pipeline.

The original source, output, parallel, PPDF, system-matrix, and plot
algorithms do not require methodological changes merely because detector
geometry changed. Their detector-specific identifiers and dimensions do
require the adaptations listed above.

## 22. Original Behavior That Must Be Preserved for Faithful Port

The following behavior should remain unchanged in the first faithful port:

- GATE/Geant4 Monte Carlo execution as the active methodology.
- PhotoElectric with StandardModel as the active gamma interaction.
- Compton and Rayleigh remaining disabled/commented as in the original
  active physics file.
- The original cut policy and process-list initialization approach, with
  only the necessary translation from old xlayer regions to the
  Magic-Cube implementation.
- Digitizer module order: Adder, energy resolution, spatial resolution,
  energy framing.
- Digitizer values: 0.10 FWHM at 140 keV, 1.0 mm spatial FWHM with
  confinement enabled, and a 120–160 keV framing window.
- No added pileup, deadtime, efficiency, optical response, or other
  detector-response model.
- The original 140 keV gamma source methodology and active source
  configuration until a separate project decision changes it.
- ROOT Hits and Singles output architecture and the fields required by
  downstream processing.
- The SPEBT control/execute order and 15 s application-time setup.
- The per-task macro-copy/substitution launcher pattern.
- The original Slurm array/dependency pattern, including any known
  limitations unless separately approved for correction.
- Separate Hits and Singles hadd processing before PPDF and system matrix.
- EventID-based Hits/Singles matching, if the objective is strict faithful
  behavior.
- The original PPDF grouping and detector-wise normalization behavior for
  an initial faithful port.
- The original system-matrix formula and long-form data organization for an
  initial faithful port.
- The original plot construction and normalization behavior unless a later
  explicit plotting change is approved.

The frozen Magic-Cube specification currently describes a different future
exposure/area-based matrix contract. That conflict must be decided
explicitly before implementing the matrix stage; it must not be silently
resolved as part of a detector-ID port.

## 23. Known Original Limitations / Risks

These are inherited implementation limitations or risks and are recorded,
not fixed, by this audit:

- Simulation runs array indices 0–100 while downstream arrays process
  1–100, so task 0 is not handled by the normal downstream stages.
- No explicit per-task random seed is configured in the active launcher.
- Hits and Singles are matched with eventID only; runID/sourceID is not
  part of the matching key.
- PPDF and system-matrix scripts assume volumeID[2] = 0 and
  volumeID[6] as a 144-detector identifier.
- The active PPDF script ultimately produces a selected-detector-0 PPDF,
  even though it loops over 144 detector IDs for highlighted metadata.
- Detector-wise normalized_count removes absolute response scale if that
  column is used as the response quantity.
- Source dimensions are data-dependent source-position groups rather than
  a fixed dense source-grid shape proven by the active code.
- par_mergesysmat.sh concatenates system-matrix Parquet files without
  deduplicating or aggregating rows.
- par_sysmatplot.sh ignores stored response columns and plots unweighted
  row occupancy.
- The plotting array comment and active range disagree.
- Some auxiliary merge/plot paths use relative output names while others
  use absolute Tridev paths; this can make path behavior dependent on the
  working directory.
- par_all.sh reuses the ppdf_job variable when submitting merge_ppdf.sh,
  so a later dependency refers to the overwritten identifier.
- The active output branch-name commands are commented; downstream scripts
  prove required branch names, but the active output macro does not
  explicitly set them.
- Empty detector/source matches are not given a clear failure or zero
  response policy before normalization.

These risks should be preserved as known original behavior during a
faithful port and addressed only by a later, explicit methodology or
robustness decision.

## 24. What Has Already Been Completed

- The V1 Magic-Cube specification is frozen in
  MAGIC_CUBE_V1_SPEC.md.
- V1 materials are defined in MAGIC_CUBE_V1_MATERIALS.md and
  GateMaterials.db, with K9 clearly marked as a provisional proxy.
- The deterministic generator and configuration exist.
- The generated Magic-Cube geometry has 4096 placements, 2048 GAGG
  positions, 2048 K9 positions, and validated map consistency.
- Static geometry validation passes with no duplicates and no placements
  outside the mother.
- The four active GAGG family sensitive-detector attachments have been
  validated in real GATE using attachCrystalSDnoSystem.
- K9 remains passive in the runtime harness.
- Raw-Hits runtime probing passed for 32 diagnostic probes.
- The external 140 keV smoke test passed.
- The runtime detector identity has been classified as
  POSITION_DERIVED_REQUIRED.
- detector_map.csv is the authoritative 0–2047 canonical detector map.
- The original repository pipeline, active files, call chain, physics,
  digitizer, source, output, parallelization, PPDF, system matrix, and
  alternative scripts have been audited in this report.

## 25. What Has NOT Yet Been Ported

In dependency order, the following production components remain:

1. Original-style Magic-Cube digitizer.
2. Original active source configuration in a production Magic-Cube source
   macro.
3. Original Hits/Singles output configuration in a production Magic-Cube
   output macro.
4. Production Magic-Cube main macro with the original control/execute
   order, geometry, GAGG sensitive-detector attachment, physics, digitizer,
   source, output, and DAQ.
5. Production simulation launcher following par_vscratch.sh.
6. Production Slurm array and dependency wiring following par_all.sh.
7. ROOT Hits/Singles merge following par_hadd.sh.
8. Magic-Cube PPDF processing with position-derived detector identity.
9. Magic-Cube system-matrix processing with 2048 mapped detectors.
10. Explicit decision and implementation for the conflict between legacy
    detector-wise normalization and the future Magic-Cube matrix contract.
11. System-matrix Parquet merge and Magic-Cube plot adaptation.
12. End-to-end production validation.

## 26. Immediate Next Implementation Step

The immediate next implementation step is:

    Port digitizer.mac into a production Magic-Cube digitizer macro and
    wire it into the future Magic-Cube main macro after initialization.

Original source file to port from:

    digitizer.mac

Magic-Cube files it must integrate with:

- magiccube_geometry.mac;
- magiccube_runtime_system.mac as the validated sensitive-detector
  attachment reference;
- magiccube_runtime_physics.mac as the PhotoElectric baseline reference;
- GateMaterials.db;
- magiccube_v1_config.json and detector_map.csv for detector-family
  identity and downstream verification.

Behavior to preserve exactly:

- Adder first;
- energy resolution second, FWHM 0.10 at 140 keV;
- spatial resolution third, FWHM 1.0 mm, confinement enabled;
- energy framing last, 120–160 keV;
- one equivalent chain for each active GAGG readout association;
- no added pileup, deadtime, efficiency, optical, or alternative response
  module.

Minimum Magic-Cube-specific adaptation:

- associate the original chain behavior with the four active GAGG family
  collections rather than xlayer1–xlayer8;
- leave K9 passive;
- preserve the no-system sensitive-detector realization proven by Step 4;
- verify that the resulting digitized collection names can feed the
  original Hits/Singles output architecture.

Likely implementation files are a new production
magiccube_digitizer.mac and the later production Magic-Cube main macro.
No implementation file is created by this audit.

Validation criterion for that future step:

- a controlled 140 keV Magic-Cube runtime must produce digitized output
  for active GAGG collections;
- the original module order and all original parameter values must be
  observable in the macro/configuration;
- K9 must produce no active detector collection;
- no PPDF, system matrix, or reconstruction code should be required to
  validate the digitizer itself.

## 27. Remaining Pipeline After the Next Step

After the digitizer is ported, the faithful implementation order is:

1. Port the original source.mac configuration.
2. Port output.mac with Hits and Singles and the required branches.
3. Build the production Magic-Cube main macro using the original sequence.
4. Build the production launcher using the original macro-copy,
   placeholder-substitution, and Gate invocation pattern.
5. Recreate the original Slurm array and afterok dependencies.
6. Reuse the original separate Hits/Singles hadd merge.
7. Port generate_ppdf_with_detectors.py to map hit positions through
   detector_map.csv and cover the 2048 active GAGG IDs.
8. Port generate_sysmat.py with the same event matching, source grouping,
   count retention, and normalization pending the explicit normalization
   decision.
9. Reuse the original Parquet merge behavior unless a deliberate change is
   approved.
10. Adapt the plotting scripts for 2048 detectors and the Magic-Cube paths
    while retaining original display semantics.
11. Perform controlled production-chain validation only after the
    individual macros and static dependencies are complete.

The Step-4 diagnostic harness should remain a regression check alongside
the production pipeline. It should not be silently promoted to the
production source/output workflow.

## 28. Final Audit Decision

The repository state is sufficiently understood to begin the next
faithful-port step: YES.

The active original pipeline is identified, its execution chain is traced,
the original detector/physics/digitizer/source/output behavior is recorded,
the active downstream algorithms are distinguished from alternatives, and
the Magic-Cube Step-4 runtime identity is proven. The next implementation
can therefore begin with the original digitizer without redesigning the
scientific methodology.

The unresolved K9 final-material question and the conflict between legacy
detector-wise normalization and the future Magic-Cube matrix contract are
explicit project decisions for later stages. Neither blocks the
digitizer-only next step. No existing project file was modified by this
audit.

### Q1. Are we still following the original Monte Carlo methodology?

YES for the active original repository: par_all.sh invokes the GATE/Geant4
Monte Carlo chain, and the active PPDF and system-matrix inputs originate
from GATE Hits and Singles ROOT outputs. The current Magic-Cube Step-4
work is diagnostic validation of that detector implementation, not a
replacement analytical methodology.

### Q2. Does current Magic-Cube physics already match original physics?

PARTIAL. The Step-4 process-selection baseline matches: both use
PhotoElectric with StandardModel and do not enable Compton or Rayleigh.
The current Magic-Cube diagnostic physics file does not reproduce the
original xlayer-specific 1.0 cm cuts or a production main-macro wiring, so
full physics-file equivalence is not yet complete.

### Q3. Which Steps 1–4 changes were unavoidable because of Magic-Cube?

- Replacing the original 144-crystal cylindricalPET/xlayer geometry with
  the 4096-position checkerboard Magic-Cube.
- Defining GAGG, K9_V1_PROXY, and Air for the new material layout.
- Keeping only the four GAGG families active and K9 passive.
- Using attachCrystalSDnoSystem for the Magic-Cube family geometry.
- Establishing position-derived canonical IDs 0–2047 through
  detector_map.csv.
- Omitting the original tungsten plate because it is not part of the
  current Magic-Cube geometry.

### Q4. Did we accidentally add any scientific methodology not present in the original active pipeline?

NO evidence of that was found. The Step-4 probes, external 140 keV smoke
test, position mapping, and validators are diagnostic infrastructure.
They do not add a production Compton/Rayleigh study, attenuation study,
response model, system-matrix formulation, or reconstruction. The future
source and matrix contracts in the V1 specification are not implemented
production methodology.

### Q5. What original pipeline component should be ported next?

The original-style digitizer from digitizer.mac should be ported next.

### Q6. What should NOT be changed in that next port?

Do not change the Adder → energy resolution → spatial resolution →
energy-framing order; the 0.10 FWHM reference at 140 keV; the 1.0 mm
spatial FWHM and confinement setting; the 120–160 keV window; or the
absence of extra pileup, deadtime, efficiency, optical, or alternative
response modules.

### Q7. What minimum Magic-Cube-specific adaptations will that next component require?

Associate the unchanged digitizer behavior with the four active GAGG
family collections instead of xlayer1–xlayer8, preserve the validated
attachCrystalSDnoSystem readout setup, leave K9 passive, and verify
compatibility with the future production Hits/Singles output.

### Pipeline Roadmap

| Roadmap item | Status |
|---|---|
| Original repository understanding | COMPLETE |
| Magic-Cube specification | COMPLETE |
| Magic-Cube materials | COMPLETE — V1 proxy caveat |
| Magic-Cube geometry | COMPLETE |
| Magic-Cube runtime geometry / detector ID | COMPLETE |
| Original-style physics | PARTIAL — process baseline matched; production integration and cuts not ported |
| Original-style digitizer | NOT YET PORTED |
| Original-style source | NOT YET PORTED |
| Original-style output | NOT YET PORTED |
| Magic-Cube production main macro | NOT YET PORTED |
| production simulation launcher | NOT YET PORTED |
| parallel Slurm workflow | NOT YET PORTED |
| ROOT merge | NOT YET PORTED |
| PPDF | NOT YET PORTED |
| system matrix | NOT YET PORTED |
| system-matrix normalization | NEEDS DECISION before matrix port |
| plots | NOT YET PORTED |

### Audit Execution Record

- Exactly seven audit passes were performed: inventory; original active
  pipeline trace; original scientific/runtime audit; downstream
  PPDF/system-matrix audit; Magic-Cube implementation audit; gap analysis;
  report creation.
- No Gate command was executed.
- No Slurm job was submitted.
- No production Python pipeline was executed.
- No system matrix was generated.
- No reconstruction was run.
- No commit, reset, revert, checkout, deletion, or existing-file edit was
  performed.
