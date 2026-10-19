#!/usr/bin/env python3
"""Voxelize OneCube Hits into a derived internal response/intensity map."""

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
    runtime_dir,
    write_json,
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
        frame = hits["frame"]
        x_column, x_raw = numeric_column(frame, "x")
        y_column, y_raw = numeric_column(frame, "y")
        z_column, z_raw = numeric_column(frame, "z")
        if x_raw is None or y_raw is None or z_raw is None:
            raise VisualizationError("Hits positions are required for cube intensity visualization")
        finite = np.isfinite(x_raw) & np.isfinite(y_raw) & np.isfinite(z_raw)
        lower, upper = cube_bounds(source)
        inside = finite.copy()
        inside &= x_raw >= lower[0] - 1e-6
        inside &= x_raw <= upper[0] + 1e-6
        inside &= y_raw >= lower[1] - 1e-6
        inside &= y_raw <= upper[1] + 1e-6
        inside &= z_raw >= lower[2] - 1e-6
        inside &= z_raw <= upper[2] + 1e-6
        if not np.any(inside):
            raise VisualizationError("no finite Hits positions fall inside the configured cube")
        positions = np.column_stack([x_raw[inside], y_raw[inside], z_raw[inside]])
        edep_column, edep_raw = numeric_column(frame, "edep")
        if edep_raw is not None and np.all(np.isfinite(edep_raw[inside])) and np.all(edep_raw[inside] >= 0):
            weights = edep_raw[inside]
            weighting = f"deposited energy branch {edep_column} [MeV]"
        else:
            weights = np.ones(len(positions), dtype=float)
            weighting = "Hit occupancy (unit weight per finite Hit)"
        bins = int(visual.get("intensity_bins", 8))
        edges = [np.linspace(lower[index], upper[index], bins + 1) for index in range(3)]
        safe_positions = np.minimum(np.maximum(positions, lower + 1e-9), upper - 1e-9)
        intensity, _ = np.histogramdd(safe_positions, bins=edges, weights=weights)
        occupied = intensity > 0
        maximum = float(np.max(intensity)) if np.any(occupied) else 0.0
        normalized = intensity / maximum if maximum > 0 else intensity
        centers = [0.5 * (edge[:-1] + edge[1:]) for edge in edges]

        fig = plt.figure(figsize=(9, 8), constrained_layout=True)
        ax = fig.add_subplot(111, projection="3d")
        cmap = plt.get_cmap("inferno")
        colors = cmap(np.where(maximum > 0, normalized, 0.0))
        if np.any(occupied):
            ax.voxels(occupied, facecolors=colors, edgecolor=(0.25, 0.25, 0.25, 0.28),
                      linewidth=0.35)
        ax.add_collection3d(Line3DCollection(cube_segments(lower, upper), colors="#0b3d91",
                                             linewidths=1.5, linestyles="--"))
        ax.set_xlabel("x [mm]")
        ax.set_ylabel("y [mm]")
        ax.set_zlabel("z [mm]")
        ax.set_xlim(lower[0], upper[0])
        ax.set_ylim(lower[1], upper[1])
        ax.set_zlim(lower[2], upper[2])
        ax.set_title(f"OneCube internal response: {weighting}")
        ax.text2D(0.02, 0.02, f"{bins} x {bins} x {bins} voxels\nnormalized to brightest voxel",
                  transform=ax.transAxes, fontsize=8)
        fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0, 1), cmap=cmap), ax=ax,
                     pad=0.12, shrink=0.7, label="normalized voxel intensity")
        path = output_dir(visual, args.config) / "cube_intensity_3d.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)

        slices = {
            "xy": (intensity.sum(axis=2), 0, 1, "x [mm]", "y [mm]", "XY"),
            "xz": (intensity.sum(axis=1), 0, 2, "x [mm]", "z [mm]", "XZ"),
            "yz": (intensity.sum(axis=0), 1, 2, "y [mm]", "z [mm]", "YZ"),
        }
        for name, (values, first, second, xlabel, ylabel, title_axis) in slices.items():
            fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
            extent = [lower[first], upper[first], lower[second], upper[second]]
            image = ax.imshow(values.T, origin="lower", extent=extent, aspect="equal", cmap="inferno")
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.set_title(f"OneCube voxel intensity slice: {title_axis} projection")
            fig.colorbar(image, ax=ax, label=weighting)
            fig.savefig(output_dir(visual, args.config) / f"cube_intensity_{name}.png", dpi=180)
            plt.close(fig)

        metadata = {
            "source": str(hits["path"]),
            "tree_name": hits["tree_name"],
            "position_branches": {"x": x_column, "y": y_column, "z": z_column},
            "weighting": weighting,
            "bin_shape": [bins, bins, bins],
            "cube_lower_mm": lower.tolist(),
            "cube_upper_mm": upper.tolist(),
            "hits_in_cube": int(np.count_nonzero(inside)),
            "hits_outside_or_nonfinite": int(len(x_raw) - np.count_nonzero(inside)),
            "total_weight": float(np.sum(weights)),
            "maximum_voxel_value": maximum,
            "classification": "derived aggregation from exact Hits positions and edep/occupancy",
        }
        write_json(runtime_dir(visual, args.config) / "cube_intensity_summary.json", metadata)
        print(f"Wrote cube intensity maps using {weighting}")
        return 0
    except (VisualizationError, OSError, ValueError) as exc:
        print(f"Cube intensity FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
