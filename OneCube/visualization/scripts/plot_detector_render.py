#!/usr/bin/env python3
"""Render the OneCube detector and source in a static 3D view."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from visualization_common import VisualizationError, cube_bounds, load_configs, output_dir


def cube_faces(lower: np.ndarray, upper: np.ndarray) -> list[list[tuple[float, float, float]]]:
    x0, y0, z0 = lower
    x1, y1, z1 = upper
    corners = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    return [
        [corners[i] for i in (0, 1, 2, 3)], [corners[i] for i in (4, 5, 6, 7)],
        [corners[i] for i in (0, 1, 5, 4)], [corners[i] for i in (2, 3, 7, 6)],
        [corners[i] for i in (1, 2, 6, 5)], [corners[i] for i in (0, 3, 7, 4)],
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="visualization config JSON")
    args = parser.parse_args()
    try:
        visual, source, _ = load_configs(args.config)
        lower, upper = cube_bounds(source)
        src = source["source"]
        source_point = np.array([src["x_mm"], src["y_mm"], src["z_mm"]], dtype=float)
        detector = source["detector"]
        fig = plt.figure(figsize=(10, 8), constrained_layout=True)
        ax = fig.add_subplot(111, projection="3d")
        faces = Poly3DCollection(cube_faces(lower, upper), facecolors="#2f81f7",
                                 edgecolors="#0b3d91", linewidths=1.5, alpha=0.65)
        ax.add_collection3d(faces)
        ax.scatter(*source_point, marker="*", s=150, color="#d1242f", edgecolor="black",
                    label="source (0, 0, -51) mm")
        ax.plot([source_point[0], detector["x_mm"]], [source_point[1], detector["y_mm"]],
                [source_point[2], detector["z_mm"]], color="#238636", linewidth=2,
                label="source-to-detector direction (+z)")
        ax.quiver(source_point[0], source_point[1], source_point[2], 0, 0, 1,
                  length=8, color="#238636", arrow_length_ratio=0.18)
        ax.text(source_point[0], source_point[1], source_point[2], "  source", color="#d1242f")
        ax.text(upper[0], upper[1], upper[2], "  GAGG cube", color="#0b3d91")
        ax.set_xlabel("x [mm]")
        ax.set_ylabel("y [mm]")
        ax.set_zlabel("z [mm]")
        ax.set_title("OneCube detector render: 2 x 2 x 2 mm GAGG")
        ax.set_xlim(-55, 5)
        ax.set_ylim(-5, 5)
        ax.set_zlim(-55, 5)
        ax.legend(loc="upper left", fontsize=9)
        ax.view_init(elev=20, azim=-62)
        path = output_dir(visual, args.config) / "detector_render.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        print(f"Wrote {path}")
        return 0
    except (VisualizationError, OSError, ValueError) as exc:
        print(f"Detector render FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
