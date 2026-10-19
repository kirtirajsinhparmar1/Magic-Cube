#!/usr/bin/env python3
"""Make a truthful cumulative Hit buildup GIF when Hit positions are available."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
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


def write_unavailable(visual: dict, args: argparse.Namespace, reason: str) -> int:
    status = {
        "supported": False,
        "output": None,
        "reason": reason,
        "trajectory_data_present": False,
        "classification": "no animation fabricated; unsupported data path documented",
    }
    write_json(runtime_dir(visual, args.config) / "animation_status.json", status)
    print(f"Animation unavailable (documented): {reason}")
    return 0


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
            return write_unavailable(visual, args, "Hits has no usable x/y/z positions")
        finite = np.isfinite(x_raw) & np.isfinite(y_raw) & np.isfinite(z_raw)
        if np.count_nonzero(finite) < 2:
            return write_unavailable(visual, args, "fewer than two finite Hit positions")
        x = x_raw[finite]
        y = y_raw[finite]
        z = z_raw[finite]
        time_column, time_raw = numeric_column(frame, "time")
        use_time = time_raw is not None and np.all(np.isfinite(time_raw[finite]))
        if use_time:
            order = np.argsort(time_raw[finite], kind="stable")
            time = time_raw[finite][order]
            basis = f"ascending {time_column} branch; cumulative positions, not trajectories"
        else:
            order = np.arange(len(x), dtype=int)
            time = None
            basis = "ROOT entry order; no physical time animation inferred"
        x, y, z = x[order], y[order], z[order]
        lower, upper = cube_bounds(source)
        configured_frames = int(visual.get("animation_frames", 12))
        frame_count = max(2, min(configured_frames, len(x)))
        cumulative_counts = np.unique(np.linspace(1, len(x), frame_count, dtype=int))
        fig = plt.figure(figsize=(8, 7), constrained_layout=True)
        ax = fig.add_subplot(111, projection="3d")
        ax.add_collection3d(Line3DCollection(cube_segments(lower, upper), colors="#0b3d91",
                                             linewidths=1.3, linestyles="--"))
        points = ax.scatter([], [], [], color="#ff7b72", s=22, alpha=0.85)
        ax.set_xlim(lower[0] - 0.1, upper[0] + 0.1)
        ax.set_ylim(lower[1] - 0.1, upper[1] + 0.1)
        ax.set_zlim(lower[2] - 0.1, upper[2] + 0.1)
        ax.set_xlabel("x [mm]")
        ax.set_ylabel("y [mm]")
        ax.set_zlabel("z [mm]")
        ax.set_title("OneCube cumulative Hit buildup")
        label = ax.text2D(0.03, 0.94, "", transform=ax.transAxes)

        def update(index: int):
            count = int(cumulative_counts[index])
            points._offsets3d = (x[:count], y[:count], z[:count])
            suffix = f"time ≤ {time[count - 1]:.5g} s" if use_time and time is not None else "ROOT entry order"
            label.set_text(f"{count:,}/{len(x):,} Hits\n{suffix}")
            return points, label

        animation = FuncAnimation(fig, update, frames=len(cumulative_counts), interval=350, blit=False)
        path = output_dir(visual, args.config) / "hit_buildup.gif"
        try:
            animation.save(path, writer=PillowWriter(fps=3))
        except Exception as exc:  # noqa: BLE001 - optional output, document exact reason
            plt.close(fig)
            return write_unavailable(visual, args, f"GIF writer failed: {exc}")
        plt.close(fig)
        write_json(runtime_dir(visual, args.config) / "animation_status.json", {
            "supported": True,
            "output": str(path),
            "frames": int(len(cumulative_counts)),
            "hits": int(len(x)),
            "basis": basis,
            "position_branches": {"x": x_column, "y": y_column, "z": z_column},
            "trajectory_data_present": False,
            "classification": "derived cumulative Hit buildup; not a reconstructed photon trajectory",
        })
        print(f"Wrote {path} using {basis}")
        return 0
    except (VisualizationError, OSError, ValueError) as exc:
        print(f"Animation preparation FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
