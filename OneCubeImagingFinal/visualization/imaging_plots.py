from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _grid_extent(voxels: list[dict[str, Any]]) -> list[float]:
    xs = sorted({float(row["x_mm"]) for row in voxels})
    ys = sorted({float(row["y_mm"]) for row in voxels})
    dx = float(np.diff(xs).min()) if len(xs) > 1 else 1.0
    dy = float(np.diff(ys).min()) if len(ys) > 1 else 1.0
    return [xs[0] - dx / 2, xs[-1] + dx / 2, ys[0] - dy / 2, ys[-1] + dy / 2]


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def render_preparation(
    project_root: Path,
    config: dict[str, Any],
    voxels: list[dict[str, Any]],
    poses: list[dict[str, Any]],
    phantom_image: np.ndarray,
    phantom_metadata: dict[str, Any],
) -> list[str]:
    output = project_root / "results" / "plots"
    output.mkdir(parents=True, exist_ok=True)
    extent = _grid_extent(voxels)
    paths = []
    fig = plt.figure(figsize=(11, 5.5))
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    ax.scatter([0], [0], [0], marker="s", s=140, color="darkorange", label="2 mm GAGG crystal")
    ax.scatter(
        [p["detector_x_mm"] for p in poses],
        [p["detector_y_mm"] for p in poses],
        [p["detector_z_mm"] for p in poses],
        marker=".", s=17, color="steelblue", label="physical detector poses",
    )
    ax.scatter(
        [v["x_mm"] for v in voxels], [v["y_mm"] for v in voxels],
        [v["z_mm"] for v in voxels], marker="x", s=17, color="crimson", label="source/image voxels",
    )
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_zlabel("z (mm)")
    ax.set_title("OneCube translated scan design")
    ax.legend(fontsize=8, loc="upper left")
    ax.view_init(elev=18, azim=-68)
    side = fig.add_subplot(1, 2, 2)
    side.scatter([0], [0], marker="s", s=110, color="darkorange", label="crystal center")
    side.scatter([0], [-51], marker="x", s=65, color="crimson", label="center source")
    side.annotate("2 mm crystal; source-facing surface at z = -1 mm", (0, 0), xytext=(5, -6))
    side.annotate("140 keV isotropic source plane; z = -51 mm", (0, -51), xytext=(5, -46))
    side.set_xlim(-20, 35)
    side.set_ylim(-60, 10)
    side.set_xlabel("x / axial z position (mm, schematic)")
    side.set_ylabel("z (mm)")
    side.grid(alpha=0.25)
    side.set_title("Center pose preserves the validated 50 mm surface gap")
    side.legend(fontsize=8)
    acquisition_path = output / "acquisition_design.png"
    _save(fig, acquisition_path)
    paths.append(str(acquisition_path.relative_to(project_root)))

    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    image = ax.imshow(phantom_image, origin="lower", extent=extent, interpolation="nearest", cmap="inferno")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title("Configured multi-hotspot phantom (pre-run design)")
    fig.colorbar(image, ax=ax, label="relative activity per voxel")
    phantom_path = output / "phantom_design.png"
    _save(fig, phantom_path)
    paths.append(str(phantom_path.relative_to(project_root)))
    return paths


def plot_system_characterization(
    project_root: Path,
    voxels: list[dict[str, Any]],
    poses: list[dict[str, Any]],
    rate: np.ndarray,
    ppdf: np.ndarray,
    sensitivity_map: np.ndarray,
    normalized_sensitivity_map: np.ndarray,
    response_masks: np.ndarray,
    fwhm: dict[str, Any],
    singular_values: np.ndarray,
) -> list[str]:
    output = project_root / "results" / "plots"
    output.mkdir(parents=True, exist_ok=True)
    extent = _grid_extent(voxels)
    paths = []
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7), constrained_layout=True)
    im = axes[0].imshow(sensitivity_map * 1.0e6, origin="lower", extent=extent, cmap="viridis")
    axes[0].set_title("Absolute sensitivity")
    axes[0].set_xlabel("x (mm)")
    axes[0].set_ylabel("y (mm)")
    fig.colorbar(im, ax=axes[0], label="cps/MBq")
    im = axes[1].imshow(normalized_sensitivity_map, origin="lower", extent=extent, vmin=0, vmax=1, cmap="viridis")
    axes[1].set_title("Sensitivity / maximum")
    axes[1].set_xlabel("x (mm)")
    axes[1].set_ylabel("y (mm)")
    fig.colorbar(im, ax=axes[1], label="fraction")
    path = output / "sensitivity_maps.png"
    _save(fig, path)
    paths.append(str(path.relative_to(project_root)))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), constrained_layout=True)
    image = axes[0].imshow(rate, aspect="auto", interpolation="nearest", cmap="magma")
    axes[0].set_title("Absolute response matrix R")
    axes[0].set_xlabel("image/source voxel j (row-major)")
    axes[0].set_ylabel("physical measurement row i")
    fig.colorbar(image, ax=axes[0], label="cps/Bq")
    central_row = len(poses) // 2
    row_image = rate[central_row].reshape(
        max(v["y_index"] for v in voxels) + 1, max(v["x_index"] for v in voxels) + 1
    )
    im = axes[1].imshow(row_image, origin="lower", extent=extent, cmap="magma")
    axes[1].set_title(f"Response map for central scan pose {central_row}")
    axes[1].set_xlabel("source x (mm)")
    axes[1].set_ylabel("source y (mm)")
    fig.colorbar(im, ax=axes[1], label="cps/Bq")
    path = output / "absolute_response.png"
    _save(fig, path)
    paths.append(str(path.relative_to(project_root)))

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), constrained_layout=True)
    axes[0].bar(np.arange(ppdf.shape[1]), ppdf[central_row], width=0.9)
    axes[0].set_xlabel("image/source voxel j")
    axes[0].set_ylabel("row-normalized response probability")
    axes[0].set_title("Representative PPDF (central pose)")
    mask_image = response_masks[central_row].reshape(row_image.shape)
    axes[1].imshow(mask_image, origin="lower", extent=extent, cmap="gray_r", vmin=0, vmax=1)
    axes[1].set_title("Response region: thresholded at configured fraction")
    axes[1].set_xlabel("source x (mm)")
    axes[1].set_ylabel("source y (mm)")
    path = output / "ppdf_and_response_mask.png"
    _save(fig, path)
    paths.append(str(path.relative_to(project_root)))

    profile_entry = fwhm["measurements"][central_row]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), constrained_layout=True)
    for axis, key, label in ((axes[0], "x_profile", "x"), (axes[1], "y_profile", "y")):
        profile = profile_entry[key]
        coords = np.asarray(profile["coordinates_mm"])
        values = np.asarray(profile["values"])
        axis.plot(coords, values, "o-", label="GATE-derived response")
        if profile.get("peak") is not None:
            axis.axhline(profile["half_maximum"], color="gray", ls="--", label="half maximum")
        if profile.get("valid"):
            axis.axvline(profile["left_crossing_mm"], color="tab:red", ls=":")
            axis.axvline(profile["right_crossing_mm"], color="tab:red", ls=":", label=f"FWHM={profile['fwhm_mm']:.3g} mm")
        else:
            axis.text(0.03, 0.95, f"FWHM invalid: {profile.get('reason')}", transform=axis.transAxes, va="top", fontsize=8)
        axis.set_xlabel(f"source {label} (mm)")
        axis.set_ylabel("response (cps/Bq)")
        axis.legend(fontsize=8)
        axis.grid(alpha=0.2)
    fig.suptitle("Central-pose profiles and half-maximum analysis")
    path = output / "response_profiles_fwhm.png"
    _save(fig, path)
    paths.append(str(path.relative_to(project_root)))

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.semilogy(np.arange(1, len(singular_values) + 1), np.maximum(singular_values, np.finfo(float).tiny), "o-")
    ax.set_xlabel("singular-value index")
    ax.set_ylabel("singular value of count operator H")
    ax.set_title("Measured response information spectrum")
    ax.grid(alpha=0.25)
    path = output / "system_matrix_singular_values.png"
    _save(fig, path)
    paths.append(str(path.relative_to(project_root)))
    return paths


def plot_reconstruction_results(
    project_root: Path,
    voxels: list[dict[str, Any]],
    phantom_image: np.ndarray,
    expected: np.ndarray,
    poisson: np.ndarray,
    gate_counts: np.ndarray,
    synthetic_estimate: np.ndarray,
    gate_estimate: np.ndarray,
    synthetic_history: dict[str, Any],
    gate_history: dict[str, Any],
    synthetic_predicted: np.ndarray,
    gate_predicted: np.ndarray,
    metrics_gate: dict[str, Any],
) -> list[str]:
    output = project_root / "results" / "plots"
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    # CSV readers return strings; normalize ordering fields before image reshaping.
    voxels = [
        {
            **voxel,
            "voxel_id": int(voxel["voxel_id"]),
            "x_index": int(voxel["x_index"]),
            "y_index": int(voxel["y_index"]),
            "x_mm": float(voxel["x_mm"]),
            "y_mm": float(voxel["y_mm"]),
        }
        for voxel in voxels
    ]
    ny = max(v["y_index"] for v in voxels) + 1
    nx = max(v["x_index"] for v in voxels) + 1
    extent = _grid_extent(voxels)
    truth = phantom_image
    gate_image = gate_estimate.reshape(ny, nx)
    error_image = gate_image - truth
    max_activity = max(float(truth.max()), float(gate_image.max()))
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.1), constrained_layout=True)
    images = [
        axes[0].imshow(truth, origin="lower", extent=extent, vmin=0, vmax=max_activity, cmap="inferno"),
        axes[1].imshow(synthetic_estimate.reshape(ny, nx), origin="lower", extent=extent, vmin=0, vmax=max_activity, cmap="inferno"),
        axes[2].imshow(gate_image, origin="lower", extent=extent, vmin=0, vmax=max_activity, cmap="inferno"),
    ]
    axes[0].set_title("True activity")
    axes[1].set_title("Synthetic Poisson MLEM")
    axes[2].set_title("Independent GATE MLEM")
    for axis in axes[:3]:
        axis.set_xlabel("x (mm)")
        axis.set_ylabel("y (mm)")
    fig.colorbar(images[0], ax=axes[:3], label="activity (Bq/voxel)", shrink=0.82)
    err_scale = max(float(np.max(np.abs(error_image))), 1.0)
    im = axes[3].imshow(error_image, origin="lower", extent=extent, vmin=-err_scale, vmax=err_scale, cmap="coolwarm")
    axes[3].set_title("GATE reconstruction error")
    axes[3].set_xlabel("x (mm)")
    axes[3].set_ylabel("y (mm)")
    fig.colorbar(im, ax=axes[3], label="reconstruction - truth (Bq/voxel)")
    path = output / "reconstruction_comparison.png"
    _save(fig, path)
    paths.append(str(path.relative_to(project_root)))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
    axes[0].plot(synthetic_history["poisson_log_likelihood"], label="synthetic Poisson")
    axes[0].plot(gate_history["poisson_log_likelihood"], label="independent GATE")
    axes[0].set_xlabel("iteration")
    axes[0].set_ylabel("Poisson log likelihood")
    axes[0].set_title("MLEM convergence")
    axes[0].legend()
    axes[0].grid(alpha=0.2)
    axes[1].plot(synthetic_history["relative_change"], label="synthetic Poisson")
    axes[1].plot(gate_history["relative_change"], label="independent GATE")
    axes[1].set_xlabel("iteration")
    axes[1].set_ylabel("relative iterate change")
    axes[1].set_title("Relative update size")
    axes[1].legend()
    axes[1].grid(alpha=0.2)
    path = output / "mlem_convergence.png"
    _save(fig, path)
    paths.append(str(path.relative_to(project_root)))

    fig, ax = plt.subplots(figsize=(11, 4.2))
    x = np.arange(expected.size)
    width = 0.27
    ax.bar(x - width, expected, width, label="expected H @ x")
    ax.bar(x, poisson, width, label="synthetic Poisson")
    ax.bar(x + width, gate_counts, width, label="independent GATE Singles")
    ax.plot(x, synthetic_predicted, "k.", ms=3, label="prediction from synthetic MLEM")
    ax.plot(x, gate_predicted, "r.", ms=3, label="prediction from GATE MLEM")
    ax.set_xlabel("physical measurement row / detector pose")
    ax.set_ylabel("accepted Singles / expected counts")
    ax.set_title("Projection data and reconstructed-model predictions")
    ax.legend(ncol=3, fontsize=8)
    ax.grid(axis="y", alpha=0.2)
    path = output / "projection_comparison.png"
    _save(fig, path)
    paths.append(str(path.relative_to(project_root)))

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.axis("off")
    lines = [
        "Independent GATE phantom reconstruction",
        f"RMSE: {metrics_gate['rmse_bq']:.5g} Bq/voxel",
        f"Normalized error: {metrics_gate['normalized_error']:.5g}",
        f"Activity recovery: {metrics_gate['activity_recovery_ratio']:.5g}",
        f"Correlation: {metrics_gate['correlation']}",
        f"Hot-region contrast recovery: {metrics_gate['hot_region_contrast_recovery']}",
        "",
        "ASCI: not physically applicable (bare uncollimated crystal)",
        "JI: null when ASCI or valid FWHM is unavailable",
    ]
    ax.text(0.03, 0.95, "\n".join(lines), va="top", family="monospace", fontsize=11)
    path = output / "reconstruction_summary.png"
    _save(fig, path)
    paths.append(str(path.relative_to(project_root)))
    return paths

