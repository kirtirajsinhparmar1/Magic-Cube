# OneCube pipeline contract

The pipeline is intentionally staged so that each stage has a clear input,
output, and failure boundary.

~~~
OneCube.mac
    |
    v
raw GATE ROOT Hits/Singles
    |
    v
hadd merged ROOT
    |
    +--> ROOT inspector --> results/validation/root_summary.json
    |
    +--> PPDF generator --> results/ppdf/ppdf.parquet
    |                       results/ppdf/ppdf.csv
    |
    +--> system matrix --> results/system_matrix/system_matrix.parquet
                            results/system_matrix/system_matrix.csv
                            results/system_matrix/system_matrix.npy
                            results/system_matrix/system_matrix_metadata.json
                            |
                            v
                         plots
                            |
                            v
                         final validation and summary
~~~

## Stage inputs and outputs

| Stage | Input | Output |
| --- | --- | --- |
| Simulation | GATE-Macro/OneCube.mac, copied GateMaterials.db | runtime/sim/*hits*.root, runtime/sim/*Singles*.root, runtime/sim/gate_exit_code.txt, runtime/logs/gate.log |
| Merge | non-empty raw ROOT files and exit code 0 | runtime/merged/hits.root, runtime/merged/singles.root |
| ROOT inspection | both merged ROOT files | results/validation/root_summary.json |
| PPDF | merged Singles ROOT and JSON config | results/ppdf/ppdf.parquet, results/ppdf/ppdf.csv |
| System matrix | merged Singles ROOT and JSON config | long-form parquet/CSV, dense .npy, metadata JSON |
| Plotting | root summary, PPDF, matrix products | results/plots/system_matrix_heatmap.png, results/plots/onecube_response_summary.png |
| Final validation | Gate exit/log, all data products, JSON config | results/validation/final_validation.json, final classification |
| Final summary | generated JSON/parquet products | compact report only; it does not recompute simulation results |

The ROOT inspector uses runID + eventID when a diagnostic event identity is
needed. Singles counts are the primary response measurement, so no
event-level Hits/Singles join is required for the 1 x 1 matrix.

Every canonical detector identity is assigned from the OneCube contract:
detector_id = 0. Native volume-ID indices are not interpreted as detector
identities.

## Slurm dependency graph

slurm/par_all.sh only submits this graph:

~~~
onecube_sim
      |
      v
onecube_merge
      |
      +-------------------+
      |                   |
      v                   v
onecube_ppdf       onecube_sysmat
      |                   |
      +---------+---------+
                v
          onecube_plot
                |
                v
       onecube_validate
~~~

The six worker jobs do one stage each. The simulation array remains
--array=0-0 so later multi-shard expansion does not require replacing the
orchestration interface.
