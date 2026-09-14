# Magic-Cube Step-5 System Compatibility Audit

## 1. Executive Decision

Final classification: **INSUFFICIENT_STATIC_EVIDENCE**.

The runtime proves that the current Step-4 system arrangement is
insufficient for the faithful original digitizer: GateSpatialResolution::Digitize
aborts because it cannot obtain the corresponding GATE system. The original
macro uses ordinary attachCrystalSD, whereas the Magic-Cube macro uses
attachCrystalSDnoSystem.

The minimum change established by the evidence is that a future production
path must provide a valid GATE system association for the four GAGG
digitizer chains. The exact supported system macro and hierarchy cannot be
proven in this bounded audit because the installed GATE 9.4 source file was
not located. No implementation is made here.

## 2. Exact Runtime Failure

The authoritative failed job was 26030041. Its log is:

    /vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5/magiccube_step5_digitizer_gate.log

The log reports GATE 9.4 with Geant4 11.2.1. Geometry initialization,
physics initialization, source initialization, and acquisition start are
reached. The fatal message is:

    G4Exception : Digitize
         issued by : GateSpatialResolution::Digitize
    Failed to get the system corresponding to that digitizer. Abort.

The job exits with code 134. The Materials.xml/optical warning is unrelated.
The separate ROOT validator NumPy import failure is also unrelated to the
GATE exception.

## 3. What Is Already Proven Working

The Step-4 closure evidence proves that the Magic-Cube geometry initializes
in real GATE 9.4, PhotoElectric-only physics reaches runtime, the bounded
source initializes, acquisition starts, and the four GAGG families produce
raw Hits with attachCrystalSDnoSystem. K9 remains passive. The Step-4
position-derived identity checks passed.

This is therefore a digitizer/system-association failure, not a Step-4
geometry or raw-Hits failure.

## 4. Original Repository System Arrangement

The original active macro is:

    GateParallel_NewConfiguration/GATE-Macro/SPEBT.mac

Its relevant order is:

    geometry.mac
        -> plate.mac
        -> system.mac
        -> physics.mac
        -> /gate/run/initialize
        -> digitizer.mac
        -> source.mac
        -> verbose.mac
        -> output.mac
        -> /gate/application/startDAQ

The original system macro attaches:

    /gate/systems/cylindricalPET/rsector/attach panel
    /gate/systems/cylindricalPET/module/attach module
    /gate/systems/cylindricalPET/submodule/attach block
    /gate/systems/cylindricalPET/crystal/attach zlayer

It then uses ordinary sensitive-detector attachment:

    /gate/xlayer1/attachCrystalSD
    /gate/xlayer2/attachCrystalSD
    /gate/xlayer3/attachCrystalSD
    /gate/xlayer4/attachCrystalSD
    /gate/xlayer5/attachCrystalSD
    /gate/xlayer6/attachCrystalSD
    /gate/xlayer7/attachCrystalSD
    /gate/xlayer8/attachCrystalSD

The original system type is cylindricalPET, with rsector, module, submodule,
and crystal levels; zlayer is attached at the crystal level and xlayer
volumes are the sensitive targets used by the digitizers.

## 5. Original Digitizer Relationship to System

The original digitizer macro creates one SinglesDigitizer chain for each
of xlayer1 through xlayer8:

    adder
        -> energyResolution
        -> spatialResolution
        -> energyFraming

Parameters are:

    energyResolution/fwhm 0.10
    energyResolution/energyOfReference 140. keV
    spatialResolution/fwhm 1.0 mm
    spatialResolution/confineInsideOfSmallestElement true
    energyFraming/setMin 120. keV
    energyFraming/setMax 160. keV

The original arrangement supplies a registered cylindricalPET system and
ordinary attachCrystalSD targets. That is why the original digitizer has a
system association available when spatialResolution runs. The exact C++
registration calls were not source-located in this bounded audit.

## 6. Current Magic-Cube Arrangement

The frozen Step-4 system macro uses:

    /gate/mc_gagg_ee/attachCrystalSDnoSystem
    /gate/mc_gagg_eo/attachCrystalSDnoSystem
    /gate/mc_gagg_oe/attachCrystalSDnoSystem
    /gate/mc_gagg_oo/attachCrystalSDnoSystem

K9 is passive. The production digitizer has four chains, for the four GAGG
families. The Step-5 bounded macro keeps the Step-4 geometry and system
macro, initializes GATE, loads the original-style chains, and starts the
bounded 140-keV check. Raw Hits worked; spatialResolution aborts.

## 7. Exact Difference Causing Failure

| Item | Original active repository | Current Magic-Cube |
|---|---|---|
| System type | cylindricalPET | No production system hierarchy |
| System levels | rsector -> module -> submodule -> crystal | None registered for GAGG |
| SD command | attachCrystalSD | attachCrystalSDnoSystem |
| Digitizer targets | xlayer1 through xlayer8 | Four mc_gagg_* families |
| Raw Hits | Available | Available |
| SpatialResolution | Works in original arrangement | Aborts on missing system |

The proven incompatibility is the missing system association, not any
original digitizer parameter.

## 8. GateSpatialResolution Source Finding

GATE source status: **SOURCE NOT LOCATED**.

The installed GATE 9.4 prefix is:

    /cvmfs/soft.ccr.buffalo.edu/versions/2023.01/easybuild/software/avx512/MPI/gcc/11.2.0/openmpi/4.1.1/gate/9.4

The bounded search within that prefix did not locate
GateSpatialResolution.cc, GateSpatialResolution.hh, or an installed GATE
source tree containing the requested implementation. No search was made
outside that prefix.

The runtime identifies the class, method, and system-related exception.
Source-level details beyond that exception are SOURCE NOT LOCATED.

## 9. System Lookup Requirement

| Question | Result | Evidence |
|---|---|---|
| System lookup function | UNKNOWN / SOURCE NOT LOCATED | The runtime names a required corresponding system; implementation was not found |
| Is lookup unconditional? | UNKNOWN / SOURCE NOT LOCATED | Failure occurs when GateSpatialResolution::Digitize executes, but its condition was not available |
| Does confineInsideOfSmallestElement control it? | UNKNOWN / SOURCE NOT LOCATED | The run cannot distinguish that flag from the module's general dependency |
| Required system information | At minimum, a corresponding GATE system association | Directly stated by the fatal runtime error |

This is enough to reject the current no-system arrangement for the complete
faithful digitizer. It is not enough to claim whether every spatial-
resolution configuration requires a system or whether the confinement
branch is the specific trigger.

## 10. attachCrystalSD vs attachCrystalSDnoSystem

| Aspect | attachCrystalSD | attachCrystalSDnoSystem |
|---|---|---|
| Original macro | Yes | No |
| Step-4 Magic-Cube macro | No | Yes |
| Raw Hits | Runtime-proven in original | Runtime-proven by Step 4 |
| System association | Present in the original working arrangement | Missing for Step-5 chain |
| Exact C++ registration | UNKNOWN / SOURCE NOT LOCATED | UNKNOWN / SOURCE NOT LOCATED |
| Runtime result here | Not the failing arrangement | GateSpatialResolution aborts |

The macro distinction and runtime consequence are proven. The runtime
warning names Readout, DeadTime, and PileUp, but the observed
SpatialResolution exception shows that this warning list is not an
exhaustive guarantee of no-system compatibility.

## 11. Candidate Solutions

Only candidates A through D are considered.

| Candidate | GATE-supported | Geometry unchanged | Original digitizer preserved | Identity unchanged | Verdict |
|---|---|---|---|---|---|
| A. Keep attachCrystalSDnoSystem exactly as-is | No for the tested chain; runtime disproves it | Yes | No; runtime aborts | Yes | Reject |
| B. New production system macro, physical geometry retained | UNKNOWN; source/runtime proof required | UNKNOWN until hierarchy is validated | Potentially yes | Yes by frozen contract | Next-task candidate, not proven |
| C. Reuse cylindricalPET as bookkeeping scaffold without moving cubes | UNKNOWN; current four-family binding is unproven | UNKNOWN | Potentially yes | Yes by frozen contract | Not justified here |
| D. Declare faithful SpatialResolution impossible without redesign | Not established | No by candidate definition | UNKNOWN | Potentially yes | Not proven; do not select |

## 12. Minimum Required Change

The minimum required change proven by the runtime is: **replace the
production no-system detector association with a new GATE-supported
system-registration path for the four GAGG digitizer chains, while leaving
the physical Magic-Cube placement and original digitizer parameters
unchanged**.

The future macro contents are not implemented or asserted here. A later
bounded task must prove whether a supported hierarchy can register the four
existing GAGG families as-is. Removing or altering spatialResolution is not
an acceptable substitute.

## 13. Impact on Frozen Detector Identity

    detector_map.csv changes: NO
    canonical formula changes: NO
    physical position mapping expected to remain valid:
    RUNTIME VALIDATION REQUIRED

The identity remains:

    hit position -> detector_map.csv -> detector_id

Any future system registration may affect GATE-native hierarchy or volume
identifiers, but it must not replace the frozen position-derived identity.

## 14. Files for the NEXT Implementation Task

No files are created or modified by this audit.

Likely future files:

    NEW:
        magiccube_production_system.mac

    REUSE:
        magiccube_geometry.mac
        magiccube_production_physics.mac
        magiccube_production_digitizer.mac
        magiccube_step5_digitizer_check.mac

    FROZEN:
        magiccube_runtime_system.mac
        detector_map.csv
        magiccube_lattice_map.csv
        magiccube_runtime_identity.json

The future task must use a separate production-system path and must not
silently replace the frozen Step-4 system macro.

## 15. Required Future Runtime Check

The next implementation task must require only:

- GATE exit code 0;
- no GateSpatialResolution::Digitize system exception;
- non-empty GAGG Hits;
- non-empty Singles;
- expected four GAGG digitizer collections, as applicable to the output
  configuration;
- physical positions still sufficient for position-derived detector mapping.

No efficiency, spectrum-shape, system-matrix, or performance criterion is
part of this bounded check.

## 16. What Must Not Change

- physical cube coordinates and dimensions;
- the 16 by 16 by 16 checkerboard;
- GAGG/K9 material assignment;
- detector_map.csv;
- the canonical detector-ID formula;
- PhotoElectric with StandardModel;
- disabled Compton and Rayleigh behavior;
- 1 cm gamma, electron, and positron cuts;
- the Adder module;
- 10 percent energy resolution at 140 keV;
- 1 mm spatial resolution;
- confineInsideOfSmallestElement true;
- the 120-160 keV window.

Removing spatialResolution, changing its 1 mm value, changing the framing
window, or enabling additional physics would violate faithful porting.

## 17. Step-5 Status

    physics: PREPARED / runtime reached successfully
    digitizer: STATIC PASS
    digitizer runtime: BLOCKED
    blocker: missing GATE system for SpatialResolution

The static digitizer preserves the original chain and values for four GAGG
families. The runtime result supersedes the earlier static assumption that
the no-system attachment was compatible with the complete chain.

    GATE_SOURCE_STATUS = NOT_LOCATED

The exact C++ lookup function, unconditionality, confinement branch, and
attachment registration calls are consequently not claimed as proven facts.

## 18. Next Action

In the next task, design and validate one new
magiccube_production_system.mac path that supplies a GATE system association
to the four existing GAGG digitizer chains without changing frozen physical
geometry, then run only the bounded Hits-to-Singles check.

This action is recommended but is not implemented here.
