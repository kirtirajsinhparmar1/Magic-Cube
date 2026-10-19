#!/usr/bin/env python3
"""Summarize Singles ROOT output and explicitly report position availability."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from visualization_common import (
    VisualizationError,
    cube_bounds,
    find_column,
    load_configs,
    load_root_dataframe,
    numeric_column,
    output_dir,
    runtime_dir,
    write_json,
    xyz_arrays,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="visualization config JSON")
    args = parser.parse_args()
    try:
        visual, source, _ = load_configs(args.config)
        singles = load_root_dataframe(visual, "singles", args.config)
        frame = singles["frame"]
        out = output_dir(visual, args.config)
        energy_column, energy = numeric_column(frame, "energy")
        time_column, time = numeric_column(frame, "time")
        energy = energy[np.isfinite(energy)] if energy is not None else np.array([])
        time = time[np.isfinite(time)] if time is not None else np.array([])

        position_available = False
        position_reason = "Singles has no usable x/y/z position branches"
        try:
            position_branches, x, y, z = xyz_arrays(singles)
            position_available = True
            position_reason = f"exact Singles position branches: {position_branches}"
        except VisualizationError as exc:
            x = y = z = np.array([])
            position_reason = str(exc)

        fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
        axes[0, 0].bar(["Singles"], [len(frame)], color="#2f81f7")
        axes[0, 0].set_ylabel("entries")
        axes[0, 0].set_title("Singles count")
        axes[0, 0].text(0, len(frame), f"{len(frame):,}", ha="center", va="bottom")
        if energy.size:
            axes[0, 1].hist(energy, bins=min(30, max(1, len(energy))), color="#238636", alpha=0.82,
                             edgecolor="white")
            axes[0, 1].set_xlabel(f"{energy_column} [MeV]")
            axes[0, 1].set_ylabel("entries")
            axes[0, 1].set_title("Singles energy")
        else:
            axes[0, 1].axis("off")
            axes[0, 1].text(0.5, 0.5, "Energy unavailable", ha="center", va="center")
        if time.size:
            axes[1, 0].hist(time, bins=min(30, max(1, len(time))), color="#8250df", alpha=0.82,
                            edgecolor="white")
            axes[1, 0].set_xlabel(f"{time_column} [s]")
            axes[1, 0].set_ylabel("entries")
            axes[1, 0].set_title("Singles time")
        else:
            axes[1, 0].axis("off")
            axes[1, 0].text(0.5, 0.5, "Time unavailable", ha="center", va="center")
        axes[1, 1].axis("off")
        axes[1, 1].text(0.5, 0.5, ("Position view available\n" + position_reason)
                        if position_available else
                        ("Position view unavailable\n" + position_reason),
                        ha="center", va="center", wrap=True,
                        bbox={"boxstyle": "round", "facecolor": "#f6f8fa"})
        fig.suptitle("OneCube Singles summary", fontsize=15)
        fig.savefig(out / "singles_summary.png", dpi=180)
        plt.close(fig)

        position_output = None
        if position_available:
            lower, upper = cube_bounds(source)
            fig = plt.figure(figsize=(8, 7), constrained_layout=True)
            ax = fig.add_subplot(111, projection="3d")
            ax.scatter(x, y, z, color="#238636", s=20, alpha=0.85)
            ax.set_xlabel("x [mm]")
            ax.set_ylabel("y [mm]")
            ax.set_zlabel("z [mm]")
            ax.set_xlim(lower[0] - 0.1, upper[0] + 0.1)
            ax.set_ylim(lower[1] - 0.1, upper[1] + 0.1)
            ax.set_zlim(lower[2] - 0.1, upper[2] + 0.1)
            ax.set_title("OneCube Singles positions (available branch data)")
            position_output = "singles_position_3d.png"
            fig.savefig(out / position_output, dpi=180)
            plt.close(fig)

        write_json(runtime_dir(visual, args.config) / "singles_availability.json", {
            "entries": int(len(frame)),
            "energy": {"available": bool(energy.size), "branch": energy_column},
            "time": {"available": bool(time.size), "branch": time_column},
            "positions": {
                "available": position_available,
                "reason": position_reason,
                "branches": position_branches if position_available else None,
                "output": position_output,
            },
            "canonical_detector_id": 0,
            "classification": "exact Singles branches; no position fabricated when absent",
        })
        print(f"Wrote {out / 'singles_summary.png'}")
        print(f"Singles position visualization: {'available' if position_available else 'unavailable'}")
        return 0
    except (VisualizationError, OSError, ValueError) as exc:
        print(f"Singles summary FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
