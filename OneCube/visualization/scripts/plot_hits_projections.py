#!/usr/bin/env python3
"""Create XY, XZ, and YZ projections of the existing Hits positions."""

from __future__ import annotations

import argparse
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
    load_root_dataframe,
    numeric_column,
    output_dir,
    xyz_arrays,
)


def projection(
    visual: dict,
    source: dict,
    args: argparse.Namespace,
    x: np.ndarray,
    y: np.ndarray,
    xlabel: str,
    ylabel: str,
    first_axis: int,
    second_axis: int,
    filename: str,
    title: str,
) -> None:
    lower, upper = cube_bounds(source)
    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
    edep_column, edep = numeric_column(args.hits["frame"], "edep")
    if edep is not None and np.all(np.isfinite(edep)):
        points = ax.scatter(x, y, c=edep, cmap="inferno", s=18, alpha=0.9)
        fig.colorbar(points, ax=ax, label=f"{edep_column} [MeV]")
    else:
        ax.scatter(x, y, color="#2f81f7", s=18, alpha=0.9)
    axis_lower = [lower[first_axis], lower[second_axis]]
    axis_upper = [upper[first_axis], upper[second_axis]]
    ax.add_patch(Rectangle((axis_lower[0], axis_lower[1]), axis_upper[0] - axis_lower[0],
                           axis_upper[1] - axis_lower[1], fill=False, edgecolor="#0b3d91",
                           linewidth=2, linestyle="--", label="GAGG bounds"))
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(axis_lower[0] - 0.1, axis_upper[0] + 0.1)
    ax.set_ylim(axis_lower[1] - 0.1, axis_upper[1] + 0.1)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title)
    ax.legend(loc="upper right")
    path = output_dir(visual, args.config) / filename
    fig.savefig(path, dpi=180)
    plt.close(fig)
    print(f"Wrote {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="visualization config JSON")
    args = parser.parse_args()
    try:
        visual, source, _ = load_configs(args.config)
        args.hits = load_root_dataframe(visual, "hits", args.config)
        _, x, y, z = xyz_arrays(args.hits)
        projection(visual, source, args, x, y, "x [mm]", "y [mm]", 0, 1,
                    "hits_projection_xy.png", "OneCube Hits projection: XY")
        projection(visual, source, args, x, z, "x [mm]", "z [mm]", 0, 2,
                    "hits_projection_xz.png", "OneCube Hits projection: XZ")
        projection(visual, source, args, y, z, "y [mm]", "z [mm]", 1, 2,
                    "hits_projection_yz.png", "OneCube Hits projection: YZ")
        return 0
    except (VisualizationError, OSError, ValueError) as exc:
        print(f"Hits projections FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
