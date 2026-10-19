"""Modular plots for the OneCube scientific imaging derivatives."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _save_map(path: Path, coords: np.ndarray, values: np.ndarray, title: str, colorbar: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    scatter = ax.scatter(coords[:, 0], coords[:, 2], c=values, s=90, cmap="viridis", edgecolors="black")
    ax.set(xlabel="x (mm)", ylabel="z (mm)", title=title)
    fig.colorbar(scatter, ax=ax, label=colorbar)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def generate_imaging_plots(
    output_dir: str | Path,
    coords: np.ndarray,
    detector_coords: np.ndarray,
    sensitivity: np.ndarray,
    response: np.ndarray,
    response_masks: np.ndarray,
    fwhm_results: list[dict[str, object]],
    asci_fraction: np.ndarray,
    phantom: np.ndarray,
    reconstruction: np.ndarray,
    expected: np.ndarray,
    measured: np.ndarray,
    history: list[dict[str, object]],
) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    _save_map(out / "source_image_grid.png", coords, np.ones(len(coords)), "OneCube source/image grid", "voxel")
    created.append("source_image_grid.png")
    _save_map(out / "sensitivity_map.png", coords, sensitivity, "Sensitivity map", "cps/Bq")
    created.append("sensitivity_map.png")
    _save_map(out / "response_map.png", coords, response.max(axis=0), "Peak spatial response", "cps/Bq")
    created.append("response_map.png")
    _save_map(out / "detector_response_map.png", detector_coords, response.sum(axis=1),
              "Response by detector measurement bin", "cps/Bq summed over voxels")
    created.append("detector_response_map.png")
    _save_map(out / "response_region_map.png", coords, response_masks.any(axis=0).astype(float), "Thresholded response region", "included")
    created.append("response_region_map.png")
    _save_map(out / "asci_map.png", coords, asci_fraction * 100.0, "Angular sampling coverage", "%")
    created.append("asci_map.png")
    _save_map(out / "phantom.png", coords, phantom.reshape(-1), "Synthetic phantom", "Bq/voxel")
    created.append("phantom.png")
    _save_map(out / "reconstruction.png", coords, reconstruction.reshape(-1), "Raw MLEM reconstruction", "Bq/voxel")
    created.append("reconstruction.png")
    _save_map(out / "reconstruction_error.png", coords, reconstruction.reshape(-1) - phantom.reshape(-1), "Reconstruction error", "Bq/voxel")
    created.append("reconstruction_error.png")

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, values, title in zip(
        axes,
        (phantom.reshape(-1), reconstruction.reshape(-1), reconstruction.reshape(-1) - phantom.reshape(-1)),
        ("True phantom", "Raw MLEM", "Error"),
    ):
        scatter = ax.scatter(coords[:, 0], coords[:, 2], c=values, s=90, cmap="viridis", edgecolors="black")
        ax.set(xlabel="x (mm)", ylabel="z (mm)", title=title)
        fig.colorbar(scatter, ax=ax, shrink=0.8)
    fig.suptitle("Phantom, reconstruction, and error")
    fig.tight_layout()
    fig.savefig(out / "reconstruction_comparison.png", dpi=150)
    plt.close(fig)
    created.append("reconstruction_comparison.png")

    fig, ax = plt.subplots(figsize=(6, 4))
    profile = fwhm_results[0] if fwhm_results else {"axis_mm": [], "profile": [], "valid": False}
    axis = np.asarray(profile.get("axis_mm", []), dtype=float)
    values = np.asarray(profile.get("profile", []), dtype=float)
    ax.plot(axis, values, marker="o", label="response profile")
    if profile.get("valid"):
        ax.axhline(float(profile["half_maximum"]), color="red", linestyle="--", label="half maximum")
        ax.axvline(float(profile["left_crossing_mm"]), color="black", linestyle=":")
        ax.axvline(float(profile["right_crossing_mm"]), color="black", linestyle=":")
    else:
        ax.text(0.03, 0.95, f"FWHM unavailable: {profile.get('reason', 'no profile')}", transform=ax.transAxes, va="top")
    ax.set(xlabel="x (mm)", ylabel="response (cps/Bq)", title="Response profile and FWHM")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out / "response_profile_fwhm.png", dpi=150)
    plt.close(fig)
    created.append("response_profile_fwhm.png")

    fig, ax = plt.subplots(figsize=(6, 4))
    indices = np.arange(len(expected))
    ax.plot(indices, expected, "o-", label="expected")
    ax.plot(indices, measured, "s", label="Poisson sample")
    ax.set(xlabel="measurement bin", ylabel="counts", title="Forward projection")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "projection_comparison.png", dpi=150)
    plt.close(fig)
    created.append("projection_comparison.png")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([int(row["iteration"]) for row in history], [float(row["relative_change"]) for row in history], marker="o")
    ax.set(xlabel="iteration", ylabel="relative change", title="MLEM convergence history")
    ax.set_yscale("log")
    fig.tight_layout()
    fig.savefig(out / "mlem_convergence.png", dpi=150)
    plt.close(fig)
    created.append("mlem_convergence.png")
    return created
