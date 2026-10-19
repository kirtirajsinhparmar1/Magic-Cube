#!/usr/bin/env python3
"""Plot existing OneCube Hits positions in 3D."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Line3DCollection

from visualization_common import (
    VisualizationError,
    cube_bounds,
    load_configs,
    load_root_dataframe,
    numeric_column,
    output_dir,
    xyz_arrays,
)


def cube_segments(lower: np.ndarray, upper: np.ndarray) -> list[np.ndarray]:
    corners = np.array([
        [lower[0], lower[1], lower[2]], [upper[0], lower[1], lower[2]],
        [upper[0], upper[1], lower[2]], [lower[0], upper[1], lower[2]],
        [lower[0], lower[1], upper[2]], [upper[0], lower[1], upper[2]],
        [upper[0], upper[1], upper[2]], [lower[0], upper[1], upper[2]],
    ])
    pairs = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
             (0, 4), (1, 5), (2, 6), (3, 7)]
    return [corners[list(pair)] for pair in pairs]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="visualization config JSON")
    args = parser.parse_args()
    try:
        visual, source, _ = load_configs(args.config)
        hits = load_root_dataframe(visual, "hits", args.config)
        branch_text, x, y, z = xyz_arrays(hits)
        edep_column, edep = numeric_column(hits["frame"], "edep")
        finite_edep = edep is not None and np.all(np.isfinite(edep))
        color_values = edep if finite_edep else "#2f81f7"
        lower, upper = cube_bounds(source)
        fig = plt.figure(figsize=(9, 8), constrained_layout=True)
        ax = fig.add_subplot(111, projection="3d")
        if finite_edep:
            scatter = ax.scatter(x, y, z, c=color_values, cmap="inferno", s=20, alpha=0.85)
            colorbar = fig.colorbar(scatter, ax=ax, pad=0.12, shrink=0.72)
            colorbar.set_label(f"{edep_column} [MeV]")
        else:
            ax.scatter(x, y, z, color=color_values, s=20, alpha=0.85)
        ax.add_collection3d(Line3DCollection(cube_segments(lower, upper), colors="#0b3d91",
                                             linewidths=1.5, linestyles="--"))
        ax.scatter([0], [0], [0], color="#0b3d91", marker="+", s=85, label="detector center")
        ax.set_xlabel("x [mm]")
        ax.set_ylabel("y [mm]")
        ax.set_zlabel("z [mm]")
        ax.set_xlim(lower[0] - 0.1, upper[0] + 0.1)
        ax.set_ylim(lower[1] - 0.1, upper[1] + 0.1)
        ax.set_zlim(lower[2] - 0.1, upper[2] + 0.1)
        ax.set_title(f"OneCube Hits: {len(x):,} positions")
        ax.text2D(0.02, 0.02, f"ROOT branches: {branch_text}\nblue dashed box: 2 mm GAGG bounds",
                  transform=ax.transAxes, fontsize=8)
        ax.legend(loc="upper left")
        path = output_dir(visual, args.config) / "hits_3d.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        print(f"Wrote {path}")
        return 0
    except (VisualizationError, OSError, ValueError) as exc:
        print(f"Hits 3D FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
