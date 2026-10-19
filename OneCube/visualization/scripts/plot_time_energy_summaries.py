#!/usr/bin/env python3
"""Create supported Hits/Singles time, energy, and event-count summaries."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from visualization_common import (
    VisualizationError,
    find_column,
    load_configs,
    load_root_dataframe,
    numeric_column,
    output_dir,
    runtime_dir,
    write_json,
)


def finite_numeric(data: dict, semantic: str) -> tuple[str | None, np.ndarray]:
    column, values = numeric_column(data["frame"], semantic)
    if values is None:
        return column, np.asarray([], dtype=float)
    return column, values[np.isfinite(values)]


def histogram_figure(values: np.ndarray, xlabel: str, title: str, path: Path, bins: int = 30) -> None:
    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    ax.hist(values, bins=min(bins, max(1, len(values))), color="#2f81f7", alpha=0.82, edgecolor="white")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("entries")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def unavailable(ax, title: str, reason: str) -> None:
    ax.axis("off")
    ax.set_title(title)
    ax.text(0.5, 0.5, f"Unavailable\n{reason}", ha="center", va="center", wrap=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="visualization config JSON")
    args = parser.parse_args()
    try:
        visual, source, _ = load_configs(args.config)
        hits = load_root_dataframe(visual, "hits", args.config)
        singles = load_root_dataframe(visual, "singles", args.config)
        out = output_dir(visual, args.config)
        availability: dict[str, dict] = {}

        hit_edep_column, hit_edep = finite_numeric(hits, "edep")
        availability["hits_edep"] = {"available": bool(hit_edep.size), "branch": hit_edep_column,
                                      "entries": int(hit_edep.size), "output": "hits_energy_hist.png",
                                      "reason": None if hit_edep.size else "edep branch absent or non-finite"}
        if hit_edep.size:
            histogram_figure(hit_edep, f"{hit_edep_column} [MeV]", "OneCube Hits deposited energy",
                             out / "hits_energy_hist.png")

        hit_time_column, hit_time = finite_numeric(hits, "time")
        availability["hits_time"] = {"available": bool(hit_time.size), "branch": hit_time_column,
                                      "entries": int(hit_time.size), "output": "hits_time_hist.png",
                                      "reason": None if hit_time.size else "time branch absent or non-finite"}
        if hit_time.size:
            histogram_figure(hit_time, f"{hit_time_column} [s]", "OneCube Hits time",
                             out / "hits_time_hist.png")

        event_column = find_column(hits["frame"], "event_id")
        if event_column is not None:
            event_values = np.asarray(hits["frame"][event_column], dtype=float)
            event_values = event_values[np.isfinite(event_values)].astype(np.int64)
        else:
            event_values = np.asarray([], dtype=np.int64)
        if event_values.size:
            _, counts = np.unique(event_values, return_counts=True)
            histogram_figure(counts.astype(float), "Hits per event", "OneCube Hits per event",
                             out / "hits_per_event_hist.png", bins=max(1, min(30, len(counts))))
        availability["hits_per_event"] = {"available": bool(event_values.size), "branch": event_column,
                                           "event_count": int(np.unique(event_values).size),
                                           "output": "hits_per_event_hist.png",
                                           "reason": None if event_values.size else "eventID branch absent or non-finite"}

        singles_energy_column, singles_energy = finite_numeric(singles, "energy")
        availability["singles_energy"] = {"available": bool(singles_energy.size), "branch": singles_energy_column,
                                           "entries": int(singles_energy.size), "output": "singles_energy_hist.png",
                                           "reason": None if singles_energy.size else "energy branch absent or non-finite"}
        if singles_energy.size:
            histogram_figure(singles_energy, f"{singles_energy_column} [MeV]", "OneCube Singles energy",
                             out / "singles_energy_hist.png")

        singles_time_column, singles_time = finite_numeric(singles, "time")
        availability["singles_time"] = {"available": bool(singles_time.size), "branch": singles_time_column,
                                         "entries": int(singles_time.size), "output": "singles_time_hist.png",
                                         "reason": None if singles_time.size else "time branch absent or non-finite"}
        if singles_time.size:
            histogram_figure(singles_time, f"{singles_time_column} [s]", "OneCube Singles time",
                             out / "singles_time_hist.png")

        fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
        panels = [
            (axes[0, 0], hit_edep, f"{hit_edep_column or 'edep'} [MeV]", "Hits deposited energy", "hits_energy_hist.png"),
            (axes[0, 1], hit_time, f"{hit_time_column or 'time'} [s]", "Hits time", "hits_time_hist.png"),
            (axes[0, 2], counts.astype(float) if event_values.size else np.array([]), "Hits per event", "Hits per event", "hits_per_event_hist.png"),
            (axes[1, 0], singles_energy, f"{singles_energy_column or 'energy'} [MeV]", "Singles energy", "singles_energy_hist.png"),
            (axes[1, 1], singles_time, f"{singles_time_column or 'time'} [s]", "Singles time", "singles_time_hist.png"),
        ]
        for ax, values, xlabel, title, _ in panels:
            if values.size:
                ax.hist(values, bins=min(30, max(1, len(values))), color="#2f81f7", alpha=0.82, edgecolor="white")
                ax.set_xlabel(xlabel)
                ax.set_ylabel("entries")
                ax.set_title(title)
                ax.grid(axis="y", alpha=0.25)
            else:
                unavailable(ax, title, "required branch absent or non-finite")
        axes[1, 2].axis("off")
        axes[1, 2].text(0.5, 0.5, f"Hits: {len(hits['frame']):,}\nSingles: {len(singles['frame']):,}\n"
                                f"source ID: {source['source']['source_id']}",
                                ha="center", va="center", fontsize=13,
                                bbox={"boxstyle": "round", "facecolor": "#f6f8fa"})
        fig.suptitle("OneCube time and energy summaries", fontsize=15)
        fig.savefig(out / "time_energy_summaries.png", dpi=180)
        plt.close(fig)
        write_json(runtime_dir(visual, args.config) / "time_energy_availability.json", {
            "classification": "exact branch distributions with derived event-count histogram",
            "plots": availability,
        })
        print(f"Wrote time/energy summary dashboard and {sum(item['available'] for item in availability.values())} branch summaries")
        return 0
    except (VisualizationError, OSError, ValueError) as exc:
        print(f"Time/energy summaries FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
