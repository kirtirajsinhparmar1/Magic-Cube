# MagicCubeFinal visualization

The authoritative plotting entry points are `../scripts/plot_positions.py` and
`../scripts/plot_system_matrix.py`. Both use a noninteractive Matplotlib backend
and save PNGs under `results/plots`.

From the project directory, use `python scripts/plot_positions.py --manifest
runtime/manifests/simulation_manifest_validation.csv` for the geometry and
source overview. After PPDF and matrix generation, use `python
scripts/plot_system_matrix.py --detector-id 0` for the full response heatmap and
the selected detector PPDF. The detector ID can be any canonical ID in 0..2047.
`PPDF_Detector_<id>.png` shows the spatial x/y PPDF separately for each source
z plane. Rectangular grids use a heatmap; irregular or degenerate grids use a
colored scatter plot, preserving every source coordinate.

Heatmap columns follow ascending canonical source ID. Values are counts per
second per Bq; raw integer counts remain separately available in
`results/system_matrix/system_matrix_raw.npy`. A detector with no counts has an
all-zero PPDF, including in the one-source validation case.

These entry points prepare or visualize artifacts only. They never submit GATE
jobs or claim runtime validation success.
