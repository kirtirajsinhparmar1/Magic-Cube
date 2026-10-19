#!/usr/bin/env python3
"""Create a source-to-detector geometry overview from the OneCube config."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from visualization_common import VisualizationError, cube_bounds, load_configs, output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="visualization config JSON")
    args = parser.parse_args()
    try:
        visual, source, _ = load_configs(args.config)
        detector = source["detector"]
        source_spec = source["source"]
        lower, upper = cube_bounds(source)
        source_x = float(source_spec["x_mm"])
        source_z = float(source_spec["z_mm"])
        surface_z = float(lower[2])
        center_distance = abs(source_z - float(detector["z_mm"]))
        surface_distance = abs(source_z - surface_z)

        fig, ax = plt.subplots(figsize=(11, 7), constrained_layout=True)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(-70, 70)
        ax.set_ylim(-58, 8)
        ax.axhline(0, color="#d0d7de", linewidth=0.8)
        ax.axvline(0, color="#d0d7de", linewidth=0.8)
        ax.add_patch(Rectangle((-70, -70), 140, 140, fill=False, linestyle="--",
                               linewidth=1.2, edgecolor="#8b949e", label="world (140 mm)",
                               transform=ax.transData))
        ax.add_patch(Rectangle((lower[0], lower[2]), upper[0] - lower[0], upper[2] - lower[2],
                               facecolor="#2f81f7", alpha=0.72, edgecolor="#0b3d91",
                               linewidth=2.0, label="2 x 2 x 2 mm GAGG cube"))
        ax.scatter([source_x], [source_z], s=120, marker="*", color="#d1242f",
                   edgecolor="black", zorder=5, label="140 keV isotropic point source")
        ax.annotate("source center\n(0, 0, -51) mm", xy=(source_x, source_z),
                    xytext=(8, source_z + 2), arrowprops={"arrowstyle": "->", "lw": 1.0},
                    fontsize=10, va="bottom")
        ax.annotate("detector center\n(0, 0, 0) mm", xy=(0, 0), xytext=(8, 4),
                    arrowprops={"arrowstyle": "->", "lw": 1.0}, fontsize=10, va="bottom")
        ax.annotate("source-facing surface\nz = -1 mm", xy=(0, surface_z), xytext=(18, surface_z - 5),
                    arrowprops={"arrowstyle": "->", "lw": 1.0}, fontsize=9)
        ax.annotate("+z source-to-detector direction", xy=(0, -18), xytext=(20, -24),
                    arrowprops={"arrowstyle": "-|>", "lw": 1.5, "color": "#238636"},
                    color="#238636", fontsize=10)
        ax.annotate("50 mm surface distance", xy=(0, surface_z), xytext=(-31, -26),
                    arrowprops={"arrowstyle": "<->", "lw": 1.1, "color": "#8250df"},
                    color="#5a32a3", ha="center", fontsize=10)
        ax.text(0, -32, f"center separation = {center_distance:g} mm", ha="center",
                color="#5a32a3", fontsize=9)
        ax.set_xlabel("x [mm] (lateral)")
        ax.set_ylabel("z [mm] (detector depth)")
        ax.set_title("OneCube geometry overview")
        ax.legend(loc="upper left", fontsize=9, framealpha=0.95)
        ax.text(0.99, 0.02, "y = 0 mm cross-section\nsource-facing side: negative z",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=9,
                bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.9})
        path = output_dir(visual, args.config) / "geometry_overview.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        print(f"Wrote {path}")
        return 0
    except (VisualizationError, OSError, ValueError) as exc:
        print(f"Geometry overview FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
