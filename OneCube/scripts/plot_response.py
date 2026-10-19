#!/usr/bin/env python3
"""Create the deliberately small OneCube matrix and response summary plots."""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT_ROOT / "results"
ROOT_SUMMARY = RESULTS / "validation" / "root_summary.json"
PPDF_PATH = RESULTS / "ppdf" / "ppdf.parquet"
MATRIX_PATH = RESULTS / "system_matrix" / "system_matrix.npy"
MATRIX_LONG_PATH = RESULTS / "system_matrix" / "system_matrix.parquet"
PLOT_DIR = RESULTS / "plots"


def main() -> int:
    with ROOT_SUMMARY.open(encoding="utf-8") as stream:
        root_summary = json.load(stream)
    ppdf = pd.read_parquet(PPDF_PATH)
    long_form = pd.read_parquet(MATRIX_LONG_PATH)
    matrix = np.load(MATRIX_PATH)

    if matrix.shape != (1, 1) or len(ppdf) != 1 or len(long_form) != 1:
        raise ValueError("plot inputs do not satisfy the OneCube one-row contract")

    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    response = float(matrix[0, 0])
    figure, axis = plt.subplots(figsize=(4.5, 3.8))
    image = axis.imshow(matrix, cmap="viridis", aspect="equal")
    axis.set_xticks([0], ["source 0"])
    axis.set_yticks([0], ["detector 0"])
    axis.set_xlabel("Source position")
    axis.set_ylabel("Detector")
    axis.set_title("OneCube system-matrix response")
    axis.text(0, 0, f"{response:.4g}", ha="center", va="center", color="white")
    figure.colorbar(image, ax=axis, label="counts / (s Bq)")
    figure.tight_layout()
    figure.savefig(PLOT_DIR / "system_matrix_heatmap.png", dpi=160)
    plt.close(figure)

    matrix_row = long_form.iloc[0]
    ppdf_row = ppdf.iloc[0]
    summary_lines = [
        "OneCube response summary",
        f"Hits: {int(root_summary['hits_count'])}",
        f"Singles: {int(root_summary['singles_count'])}",
        f"Raw matrix count: {int(matrix_row['raw_singles_count'])}",
        f"cps/MBq: {float(matrix_row['response_cps_per_MBq']):.6g}",
        f"PPDF: {float(ppdf_row['ppdf']):.6g}",
    ]
    figure, axis = plt.subplots(figsize=(7.0, 4.0))
    axis.axis("off")
    axis.text(0.03, 0.95, "\n".join(summary_lines), va="top", ha="left", family="monospace", fontsize=12)
    figure.tight_layout()
    figure.savefig(PLOT_DIR / "onecube_response_summary.png", dpi=160)
    plt.close(figure)

    print("Plots written: system_matrix_heatmap.png, onecube_response_summary.png")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001 - stage must fail loudly
        print(f"Plot generation failed: {error}", file=sys.stderr)
        sys.exit(1)
