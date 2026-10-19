#!/usr/bin/env python3
"""Create a compact setup, count, PPDF, and system-response dashboard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

from visualization_common import (
    VisualizationError,
    cube_bounds,
    load_configs,
    output_dir,
    read_csv_rows,
    runtime_dir,
    write_json,
)


def _load_json(path: Path) -> dict:
    if not path.is_file():
        raise VisualizationError(f"required visualization summary does not exist: {path}")
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="visualization config JSON")
    args = parser.parse_args()
    try:
        visual, source, source_path = load_configs(args.config)
        project_root = source_path.parents[1]
        visual_runtime = runtime_dir(visual, args.config)
        inspection = _load_json(visual_runtime / "root_inspection.json")
        ppdf_rows = read_csv_rows(project_root / "results" / "ppdf" / "ppdf.csv")
        matrix_rows = read_csv_rows(project_root / "results" / "system_matrix" / "system_matrix.csv")
        if len(ppdf_rows) != 1 or len(matrix_rows) != 1:
            raise VisualizationError("OneCube dashboard expects exactly one PPDF row and one matrix row")
        ppdf = float(ppdf_rows[0]["ppdf"])
        raw_count = int(float(matrix_rows[0]["raw_singles_count"]))
        cps_mbq = float(matrix_rows[0]["response_cps_per_MBq"])
        response_per_bq_s = float(matrix_rows[0]["response_per_Bq_s"])
        gate_exit_path = project_root / "runtime" / "sim" / "gate_exit_code.txt"
        gate_exit = gate_exit_path.read_text().strip() if gate_exit_path.is_file() else "not recorded"

        detector = source["detector"]
        source_spec = source["source"]
        lower, upper = cube_bounds(source)
        fig = plt.figure(figsize=(14, 8), constrained_layout=True)
        grid = fig.add_gridspec(2, 3, width_ratios=[1.25, 1, 1])
        ax_setup = fig.add_subplot(grid[:, 0])
        ax_setup.set_aspect("equal", adjustable="box")
        ax_setup.set_xlim(-56, 5)
        ax_setup.set_ylim(-54, 5)
        ax_setup.add_patch(Rectangle((lower[0], lower[2]), upper[0] - lower[0], upper[2] - lower[2],
                                     color="#2f81f7", alpha=0.7))
        ax_setup.scatter([source_spec["x_mm"]], [source_spec["z_mm"]], marker="*", s=140,
                         color="#d1242f", edgecolor="black")
        ax_setup.plot([source_spec["x_mm"], detector["x_mm"]],
                      [source_spec["z_mm"], detector["z_mm"]], color="#238636", linewidth=2)
        ax_setup.annotate("source\n(0,0,-51) mm", xy=(0, -51), xytext=(3, -49),
                          arrowprops={"arrowstyle": "->"}, fontsize=9)
        ax_setup.annotate("2 mm GAGG\ncenter (0,0,0)", xy=(0, 0), xytext=(3, 2),
                          arrowprops={"arrowstyle": "->"}, fontsize=9)
        ax_setup.set_xlabel("x [mm]")
        ax_setup.set_ylabel("z [mm]")
        ax_setup.set_title("Setup sketch")
        ax_setup.text(0.03, 0.03, "negative z is source-facing\n50 mm to cube surface",
                      transform=ax_setup.transAxes, fontsize=8,
                      bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.9})

        ax_counts = fig.add_subplot(grid[0, 1])
        hit_count = int(inspection["hits"]["entry_count"])
        singles_count = int(inspection["singles"]["entry_count"])
        bars = ax_counts.bar(["Hits", "Singles"], [hit_count, singles_count],
                             color=["#8250df", "#238636"])
        ax_counts.set_title("ROOT entries")
        ax_counts.set_ylabel("entries")
        for bar in bars:
            ax_counts.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{int(bar.get_height()):,}",
                           ha="center", va="bottom")

        ax_response = fig.add_subplot(grid[0, 2])
        image = ax_response.imshow(np.array([[response_per_bq_s]]), cmap="viridis", aspect="auto")
        ax_response.set_xticks([0], ["source 0"])
        ax_response.set_yticks([0], ["detector 0"])
        ax_response.set_title("1 x 1 normalized response")
        ax_response.text(0, 0, f"{response_per_bq_s:.4g}\ncounts/(s Bq)", ha="center", va="center",
                         color="white", fontweight="bold")
        fig.colorbar(image, ax=ax_response, fraction=0.046, pad=0.04)

        ax_metrics = fig.add_subplot(grid[1, 1:])
        ax_metrics.axis("off")
        metrics = (
            f"PPDF p₀₀: {ppdf:g}\n"
            f"raw Singles count n₀₀: {raw_count:,}\n"
            f"response: {response_per_bq_s:.6g} counts/(s·Bq)\n"
            f"response: {cps_mbq:.6g} cps/MBq\n"
            f"Gate exit code: {gate_exit}\n"
            f"Hits inside cube: {inspection['hits']['positions'].get('within_detector')}\n"
            "PPDF/matrix values: existing OneCube products"
        )
        ax_metrics.text(0.03, 0.9, metrics, va="top", fontsize=13,
                        bbox={"boxstyle": "round", "facecolor": "#f6f8fa", "edgecolor": "#d0d7de"})
        fig.suptitle("OneCube source-response summary", fontsize=17)
        path = output_dir(visual, args.config) / "response_dashboard.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        write_json(visual_runtime / "dashboard_summary.json", {
            "hits": hit_count,
            "singles": singles_count,
            "ppdf": ppdf,
            "raw_singles_count": raw_count,
            "response_per_Bq_s": response_per_bq_s,
            "response_cps_per_MBq": cps_mbq,
            "gate_exit_code": gate_exit,
            "classification": "dashboard reads exact existing ROOT inspection and PPDF/system-matrix products",
        })
        print(f"Wrote {path}")
        return 0
    except (VisualizationError, OSError, ValueError, KeyError) as exc:
        print(f"Response dashboard FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
