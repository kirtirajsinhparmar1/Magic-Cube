from __future__ import annotations

import csv
import json
import os
import shutil
import textwrap
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

os.environ.setdefault("MPLCONFIGDIR", "/tmp/magiccube-mplconfig")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.patches import FancyArrowPatch, Rectangle
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[3]
MCSIM = ROOT / "mcsim"
ONE = MCSIM / "OneCube"
MAGIC = MCSIM / "MagicCubeFinal"
OUT = MAGIC / "meeting_slides"
FIG = OUT / "figures"
SLIDES = OUT / "slides"

NAVY = "#0B1220"
PANEL = "#131F33"
PANEL2 = "#17263D"
WHITE = "#F5F8FC"
MUTED = "#A7B7C9"
CYAN = "#58D7FF"
ORANGE = "#FFB86B"
GREEN = "#39D98A"
RED = "#FF6B6B"
PURPLE = "#B9A0FF"
GRID = "#2C3C52"


def read_json(path: Path):
    return json.loads(path.read_text())


def savefig(fig, path: Path, dpi=150):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def copy_asset(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def load_detector_map():
    rows = []
    with (MAGIC / "config/detector_map.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    out = {k: np.array([float(r[k]) for r in rows]) for k in ["detector_id", "ix", "iy", "d", "physical_layer_k", "depth_index", "x_mm", "y_mm", "z_mm"]}
    return out


def load_magic_data():
    dm = load_detector_map()
    raw = np.load(MAGIC / "results/system_matrix/system_matrix_raw.npy")[:, 0]
    response = np.load(MAGIC / "results/system_matrix/system_matrix.npy")[:, 0]
    return dm, raw, response


def marker_counts_and_grid():
    marker_dir = MAGIC / "runtime/sim/full"
    state = {}
    for p in sorted(marker_dir.glob("task_*.exit_code.txt")):
        try:
            tid = int(p.name.split("_")[1].split(".")[0])
            state[tid] = p.read_text().strip()
        except (ValueError, OSError):
            continue
    grid = np.full((51, 51), -1, dtype=int)
    # source_grid_config defines y outer / x inner; task/source IDs are 0..2600.
    for sid, value in state.items():
        if sid >= 2601:
            continue
        iy, ix = divmod(sid, 51)
        grid[iy, ix] = {"0": 0, "1": 1, "RUNNING": 2}.get(value, 3)
    counts = {"0": sum(v == "0" for v in state.values()), "1": sum(v == "1" for v in state.values()), "RUNNING": sum(v == "RUNNING" for v in state.values())}
    counts["other"] = len(state) - sum(counts.values())
    return state, grid, counts


def draw_cube(ax, x, y, z, size, color, alpha=0.9, edgecolor="none"):
    # Lightweight wireframe cube used only for the OneCube explanatory figure.
    s = size / 2
    pts = np.array([[x + dx * s, y + dy * s, z + dz * s] for dx, dy, dz in [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]])
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
    for a, b in edges:
        ax.plot(*zip(pts[a], pts[b]), color=color, alpha=alpha, linewidth=1.5)


def make_assets():
    FIG.mkdir(parents=True, exist_ok=True)
    # Stable, already-generated OneCube / MagicCube figures are copied rather than recreated.
    copy_asset(ONE / "visualization/outputs/detector_render.png", FIG / "onecube_geometry_existing.png")
    copy_asset(ONE / "visualization/outputs/hits_3d.png", FIG / "onecube_hits_existing.png")
    copy_asset(ONE / "visualization/outputs/singles_position_3d.png", FIG / "onecube_singles_existing.png")
    copy_asset(ONE / "visualization/outputs/response_dashboard.png", FIG / "onecube_response_dashboard_existing.png")
    copy_asset(MAGIC / "results/plots/positions.png", FIG / "magiccube_positions_existing.png")
    copy_asset(MAGIC / "results/plots/system_matrix_heatmap.png", FIG / "magiccube_heatmap_existing.png")

    dm, raw, response = load_magic_data()
    cfg = read_json(MAGIC / "config/magiccube_config.json")
    state, grid, marker_counts = marker_counts_and_grid()

    # OneCube pipeline schematic.
    fig, ax = plt.subplots(figsize=(14, 4), facecolor=NAVY)
    ax.set_facecolor(NAVY)
    ax.axis("off")
    nodes = [(0.03, "140 keV\npoint source", CYAN), (0.21, "GATE\ntransport", PURPLE), (0.40, "Hits\nROOT", ORANGE), (0.59, "Singles\nROOT", ORANGE), (0.78, "PPDF +\n1×1 matrix", GREEN)]
    for i, (x, label, color) in enumerate(nodes):
        ax.text(x + 0.07, 0.55, label, ha="center", va="center", color=WHITE, fontsize=17, weight="bold", linespacing=1.2,
                bbox=dict(boxstyle="round,pad=0.7", facecolor=PANEL2, edgecolor=color, linewidth=2))
        if i < len(nodes) - 1:
            ax.add_patch(FancyArrowPatch((x + 0.145, 0.55), (nodes[i + 1][0] - 0.025, 0.55), arrowstyle="-|>", mutation_scale=18, linewidth=2, color=MUTED))
    ax.text(0.5, 0.13, "ONECUBE_END_TO_END_PASS   •   233 Hits   •   233 Singles   •   ppdf = 1.0", ha="center", color=GREEN, fontsize=16, weight="bold")
    savefig(fig, FIG / "onecube_pipeline.png")

    # Scaling visual: one tile to the full 16×16×16 interleaved lattice.
    fig, ax = plt.subplots(figsize=(14, 4.4), facecolor=NAVY)
    ax.set_facecolor(NAVY)
    ax.axis("off")
    for i in range(16):
        for j in range(16):
            ax.add_patch(Rectangle((0.08 + j * 0.018, 0.25 + i * 0.018), 0.015, 0.015, facecolor=CYAN if (i + j) % 2 == 0 else ORANGE, edgecolor="none"))
    ax.add_patch(Rectangle((0.09, 0.53), 0.055, 0.055, facecolor=CYAN, edgecolor=WHITE, linewidth=1.5))
    ax.text(0.11, 0.16, "OneCube\n1 GAGG", ha="center", color=WHITE, fontsize=16, weight="bold")
    ax.add_patch(FancyArrowPatch((0.23, 0.53), (0.46, 0.53), arrowstyle="-|>", mutation_scale=22, linewidth=2.5, color=GREEN))
    ax.text(0.345, 0.66, "same validated pipeline", ha="center", color=GREEN, fontsize=14, weight="bold")
    for k in range(4):
        off = 0.48 + k * 0.075
        for i in range(16):
            for j in range(16):
                ax.add_patch(Rectangle((off + j * 0.0041, 0.36 + i * 0.0041 + k * 0.028), 0.0034, 0.0034, facecolor=CYAN if (i + j + k) % 2 == 0 else ORANGE, edgecolor="none"))
    ax.text(0.67, 0.16, "MagicCube\n2048 GAGG + 2048 K9\n16 interleaved layers", ha="center", color=WHITE, fontsize=16, weight="bold")
    ax.text(0.92, 0.5, "67.2 × 67.2 × 32 mm", ha="center", color=CYAN, fontsize=17, weight="bold", rotation=90)
    savefig(fig, FIG / "magiccube_scaling.png")

    # Full detector geometry, using canonical detector map plus the complementary K9 lattice positions.
    nx = ny = nz = 16
    pitch = 4.2
    zpitch = 2.0
    gagg = []
    k9 = []
    for k in range(nz):
        for iy in range(ny):
            for ix in range(nx):
                x = (ix - 7.5) * pitch
                y = (iy - 7.5) * pitch
                z = (k - 7.5) * zpitch
                (gagg if (ix + iy + k) % 2 == 0 else k9).append((x, y, z))
    gagg = np.asarray(gagg)
    k9 = np.asarray(k9)
    fig = plt.figure(figsize=(10, 7), facecolor=NAVY)
    ax = fig.add_subplot(111, projection="3d", facecolor=NAVY)
    ax.scatter(k9[:, 0], k9[:, 1], k9[:, 2], s=5, c="#77879A", alpha=0.32, label="K9 (proxy, insensitive)")
    ax.scatter(gagg[:, 0], gagg[:, 1], gagg[:, 2], s=7, c=CYAN, alpha=0.75, label="GAGG (sensitive)")
    ax.scatter([0], [0], [-66], s=90, c=ORANGE, marker="*", label="140 keV source")
    ax.plot([0, 0], [0, 0], [-66, -16], color=ORANGE, linewidth=1.5, alpha=0.7)
    ax.set_xlabel("x (mm)", color=WHITE, labelpad=8)
    ax.set_ylabel("y (mm)", color=WHITE, labelpad=8)
    ax.set_zlabel("z (mm)", color=WHITE, labelpad=8)
    ax.set_title("Full MagicCube lattice • source-facing side at z = −16 mm", color=WHITE, fontsize=15, weight="bold", pad=14)
    ax.legend(loc="upper left", fontsize=9, facecolor=PANEL, edgecolor=GRID, labelcolor=WHITE)
    ax.set_xlim(-40, 40); ax.set_ylim(-40, 40); ax.set_zlim(-70, 18)
    ax.xaxis.set_pane_color((0.04, 0.07, 0.12, 1)); ax.yaxis.set_pane_color((0.04, 0.07, 0.12, 1)); ax.zaxis.set_pane_color((0.04, 0.07, 0.12, 1))
    ax.tick_params(colors=MUTED)
    savefig(fig, FIG / "magiccube_geometry_3d.png")

    # Layer / checkerboard structure.
    fig, axes = plt.subplots(1, 4, figsize=(14, 4), facecolor=NAVY)
    for ax, k in zip(axes, [0, 1, 8, 15]):
        ax.set_facecolor(PANEL)
        for iy in range(16):
            for ix in range(16):
                color = CYAN if (ix + iy + k) % 2 == 0 else ORANGE
                ax.add_patch(Rectangle((ix, iy), 1, 1, facecolor=color, edgecolor=NAVY, linewidth=0.35))
        ax.set_xlim(0, 16); ax.set_ylim(0, 16); ax.set_aspect("equal")
        ax.set_title(f"physical layer k = {k}", color=WHITE, fontsize=12, weight="bold")
        ax.set_xticks([]); ax.set_yticks([])
    fig.text(0.5, 0.02, "Depth layers alternate the checkerboard phase: each source-facing ray sees GAGG / K9 interleaving along z.", ha="center", color=MUTED, fontsize=13)
    fig.text(0.5, 0.98, "GAGG = sensitive   •   K9 = interleaved absorber / spacer proxy", ha="center", color=WHITE, fontsize=15, weight="bold", va="top")
    savefig(fig, FIG / "layer_checkerboard_exploded.png")

    # Validated response map on actual canonical GAGG positions.
    fig = plt.figure(figsize=(10, 7), facecolor=NAVY)
    ax = fig.add_subplot(111, projection="3d", facecolor=NAVY)
    norm = Normalize(vmin=float(raw.min()), vmax=float(raw.max()))
    sc = ax.scatter(dm["x_mm"], dm["y_mm"], dm["z_mm"], c=raw, cmap="magma", norm=norm, s=26, alpha=0.95, edgecolors="none")
    ax.scatter([0], [0], [-66], s=110, c=CYAN, marker="*", label="source (0, 0, −66 mm)")
    ax.set_title("Validated 2048-detector response • Singles count per GAGG position", color=WHITE, fontsize=15, weight="bold", pad=14)
    ax.set_xlabel("x (mm)", color=WHITE); ax.set_ylabel("y (mm)", color=WHITE); ax.set_zlabel("z (mm)", color=WHITE)
    ax.legend(loc="upper left", fontsize=9, facecolor=PANEL, edgecolor=GRID, labelcolor=WHITE)
    cb = fig.colorbar(sc, ax=ax, shrink=0.7, pad=0.1); cb.set_label("validated Singles count", color=WHITE); cb.ax.yaxis.set_tick_params(color=WHITE); plt.setp(cb.ax.get_yticklabels(), color=WHITE)
    ax.xaxis.set_pane_color((0.04, 0.07, 0.12, 1)); ax.yaxis.set_pane_color((0.04, 0.07, 0.12, 1)); ax.zaxis.set_pane_color((0.04, 0.07, 0.12, 1)); ax.tick_params(colors=MUTED)
    savefig(fig, FIG / "validated_detector_response.png")

    # Depth aggregation, with small representative 16x16 maps.
    layer = dm["physical_layer_k"].astype(int)
    layer_sums = np.array([raw[layer == k].sum() for k in range(16)])
    fig = plt.figure(figsize=(14, 5.2), facecolor=NAVY)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.25, 1], wspace=0.22)
    ax = fig.add_subplot(gs[0], facecolor=PANEL)
    ax.bar(np.arange(16), layer_sums, color=[CYAN if k % 2 == 0 else ORANGE for k in range(16)], edgecolor="none")
    ax.set_title("Validated Singles aggregated by physical layer", color=WHITE, fontsize=14, weight="bold")
    ax.set_xlabel("physical layer k (source-facing k = 0)", color=WHITE); ax.set_ylabel("Singles count", color=WHITE)
    ax.set_xticks(range(16)); ax.tick_params(colors=MUTED); ax.grid(axis="y", color=GRID, alpha=0.6); [s.set_color(GRID) for s in ax.spines.values()]
    right = gs[1].subgridspec(1, 4, wspace=0.1)
    vmax = raw.max()
    for ax, k in zip([fig.add_subplot(right[0]), fig.add_subplot(right[1]), fig.add_subplot(right[2]), fig.add_subplot(right[3])], [0, 5, 10, 15]):
        arr = np.full((16, 16), np.nan)
        for ix, iy, count, lk in zip(dm["ix"].astype(int), dm["iy"].astype(int), raw, layer):
            if lk == k: arr[iy, ix] = count
        ax.imshow(arr, origin="lower", cmap="magma", vmin=0, vmax=vmax)
        ax.set_title(f"k={k}", color=WHITE, fontsize=11); ax.set_xticks([]); ax.set_yticks([])
    fig.text(0.5, 0.98, "Layer response is computed from the validated 2048×1 Singles vector", ha="center", va="top", color=WHITE, fontsize=15, weight="bold")
    savefig(fig, FIG / "validated_layer_response.png")

    # Full-FOV architecture.
    fig, ax = plt.subplots(figsize=(14, 4.8), facecolor=NAVY)
    ax.set_facecolor(NAVY); ax.axis("off")
    blocks = [(0.05, "51 × 51 grid\n2,601 source positions\n(x,y,z = −66 mm)", CYAN), (0.38, "one source →\n2048-element vector\n(raw Singles)", ORANGE), (0.71, "aggregate columns →\n2048 × 2,601\nsystem matrix", GREEN)]
    for x, label, color in blocks:
        ax.text(x + 0.115, 0.53, label, ha="center", va="center", color=WHITE, fontsize=16, weight="bold", linespacing=1.25,
                bbox=dict(boxstyle="round,pad=0.85", facecolor=PANEL2, edgecolor=color, linewidth=2.4))
    ax.add_patch(FancyArrowPatch((0.29, 0.53), (0.37, 0.53), arrowstyle="-|>", mutation_scale=20, linewidth=2.5, color=MUTED))
    ax.add_patch(FancyArrowPatch((0.62, 0.53), (0.70, 0.53), arrowstyle="-|>", mutation_scale=20, linewidth=2.5, color=MUTED))
    ax.text(0.5, 0.13, "raw ROOT files → per-source reduction → canonical detector/source ordering", ha="center", color=MUTED, fontsize=14)
    savefig(fig, FIG / "full_fov_architecture.png")

    # Marker-only production progress. No runtime values are inferred from missing matrix outputs.
    fig, ax = plt.subplots(figsize=(9.5, 7.1), facecolor=NAVY)
    ax.set_facecolor(PANEL)
    cmap = plt.matplotlib.colors.ListedColormap(["#566A7F", GREEN, RED, ORANGE])
    ax.imshow(grid, origin="lower", extent=(-51, 51, -51, 51), cmap=cmap, vmin=-1, vmax=2, interpolation="nearest", aspect="equal")
    ax.set_xlabel("source x (mm)", color=WHITE); ax.set_ylabel("source y (mm)", color=WHITE); ax.tick_params(colors=MUTED)
    ax.set_title("Completion markers at generation time", color=WHITE, fontsize=15, weight="bold")
    for value, color, label in [(0, GREEN, f"completed exit 0: {marker_counts['0']}"), (1, RED, f"exit 1: {marker_counts['1']}"), (2, ORANGE, f"running: {marker_counts['RUNNING']}")]:
        ax.scatter([], [], c=color, s=65, label=label)
    ax.legend(loc="upper right", facecolor=PANEL2, edgecolor=GRID, labelcolor=WHITE, fontsize=10)
    fig.text(0.5, 0.02, "PARTIAL PRODUCTION — NOT FINAL SCIENTIFIC RESULT", ha="center", color=RED, fontsize=16, weight="bold")
    savefig(fig, FIG / "full_fov_progress.png")
    return dm, raw, response, cfg, marker_counts


def slide_base(number, title, kicker="MEETING UPDATE"):
    fig = plt.figure(figsize=(13.333, 7.5), dpi=144, facecolor=NAVY)
    fig.text(0.055, 0.925, kicker, color=CYAN, fontsize=10, weight="bold", family="DejaVu Sans")
    fig.text(0.055, 0.855, title, color=WHITE, fontsize=29, weight="bold", family="DejaVu Sans")
    fig.add_artist(plt.Line2D([0.055, 0.945], [0.825, 0.825], color=GRID, linewidth=1))
    fig.text(0.055, 0.035, "MagicCube • OneCube → full MagicCube", color=MUTED, fontsize=9)
    fig.text(0.945, 0.035, f"{number:02d} / 13", color=MUTED, fontsize=9, ha="right")
    return fig


def text_box(fig, x, y, w, h, title, body, color=CYAN, body_size=15):
    ax = fig.add_axes([x, y, w, h]); ax.set_facecolor(PANEL); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=PANEL, edgecolor=GRID, linewidth=1.2))
    ax.text(0.06, 0.82, title, transform=ax.transAxes, color=color, fontsize=13, weight="bold", va="top")
    wrap_width = max(20, int(105 * w * 15 / max(body_size, 1)))
    wrapped = "\n".join(textwrap.fill(line, width=wrap_width) if line.strip() else "" for line in body.splitlines())
    ax.text(0.06, 0.63, wrapped, transform=ax.transAxes, color=WHITE, fontsize=body_size, va="top", linespacing=1.35)
    return ax


def image_panel(fig, path, rect, title=None):
    ax = fig.add_axes(rect); ax.set_facecolor(PANEL); ax.axis("off")
    im = Image.open(path).convert("RGB")
    ax.imshow(im)
    if title:
        ax.text(0.02, 0.98, title, transform=ax.transAxes, va="top", color=WHITE, fontsize=11, weight="bold", bbox=dict(facecolor=NAVY, alpha=0.75, edgecolor="none", pad=3))
    return ax


def make_slides(dm, raw, response, cfg, marker_counts):
    SLIDES.mkdir(parents=True, exist_ok=True)
    one_validation = read_json(ONE / "results/validation/final_validation.json")
    magic_validation = read_json(MAGIC / "results/validation/runtime_validation_validation.json")
    summary = read_json(MAGIC / "results/final_summary_validation.json")
    hits = 189964; singles = int(raw.sum())
    slide_paths = []

    # 1
    fig = plt.figure(figsize=(13.333, 7.5), dpi=144, facecolor=NAVY)
    fig.text(0.06, 0.78, "MagicCube", color=WHITE, fontsize=54, weight="bold")
    fig.text(0.06, 0.68, "Meeting progress update", color=CYAN, fontsize=32, weight="bold")
    fig.text(0.06, 0.48, "Goal: reproduce the Magic-Cube self-collimating\ngamma camera in GATE / mcsim", color=WHITE, fontsize=24, linespacing=1.35)
    fig.text(0.06, 0.18, "OneCube", color=ORANGE, fontsize=20, weight="bold")
    fig.text(0.28, 0.18, "→", color=MUTED, fontsize=25, weight="bold")
    fig.text(0.39, 0.18, "MagicCube", color=CYAN, fontsize=20, weight="bold")
    fig.text(0.64, 0.18, "→", color=MUTED, fontsize=25, weight="bold")
    fig.text(0.75, 0.18, "full-FOV production", color=GREEN, fontsize=20, weight="bold")
    # Decorative detector motif.
    for k in range(7):
        for i in range(7):
            fig.add_artist(Rectangle((0.74 + i * 0.026 + k * 0.004, 0.45 + k * 0.026), 0.021, 0.021, transform=fig.transFigure, facecolor=CYAN if (i + k) % 2 == 0 else ORANGE, alpha=0.72, edgecolor=NAVY, linewidth=0.5))
    fig.text(0.06, 0.045, "Validated single-source result is complete; full-FOV run is still partial production.", color=MUTED, fontsize=11)
    slide_paths.append(SLIDES / "slide_01_title.png"); savefig(fig, slide_paths[-1])

    # 2
    fig = slide_base(2, "Why start with OneCube?", "01 • REDUCE RISK")
    image_panel(fig, FIG / "onecube_geometry_existing.png", [0.055, 0.18, 0.40, 0.57], "actual OneCube geometry")
    text_box(fig, 0.50, 0.50, 0.40, 0.25, "The smallest useful proof", "• one 2 × 2 × 2 mm GAGG cube\n• 140 keV point source at z = −51 mm\n• isolates source → transport → readout → matrix")
    text_box(fig, 0.50, 0.19, 0.40, 0.22, "Message", "A compact geometry made it possible to validate the entire data path before scaling detector count and depth.", GREEN, 15)
    slide_paths.append(SLIDES / "slide_02_onecube_motivation.png"); savefig(fig, slide_paths[-1])

    # 3
    fig = slide_base(3, "OneCube end-to-end pipeline", "02 • PIPELINE PROOF")
    image_panel(fig, FIG / "onecube_pipeline.png", [0.055, 0.28, 0.89, 0.43])
    text_box(fig, 0.10, 0.12, 0.25, 0.11, "PASS", "233 Hits → 233 Singles", GREEN, 13)
    text_box(fig, 0.38, 0.12, 0.25, 0.11, "PPDF", "1 detector / 1 source", CYAN, 13)
    text_box(fig, 0.66, 0.12, 0.25, 0.11, "MATRIX", "1 × 1 response", ORANGE, 13)
    slide_paths.append(SLIDES / "slide_03_onecube_pipeline.png"); savefig(fig, slide_paths[-1])

    # 4
    fig = slide_base(4, "OneCube visual results", "03 • VALIDATED ONECUBE")
    image_panel(fig, FIG / "onecube_hits_existing.png", [0.055, 0.35, 0.27, 0.40], "Hits in cube")
    image_panel(fig, FIG / "onecube_singles_existing.png", [0.365, 0.35, 0.27, 0.40], "Singles positions")
    image_panel(fig, FIG / "onecube_response_dashboard_existing.png", [0.675, 0.32, 0.27, 0.44], "response / matrix dashboard")
    fig.text(0.055, 0.19, "Geometry", color=ORANGE, fontsize=16, weight="bold")
    fig.text(0.365, 0.19, "Hits / Singles", color=CYAN, fontsize=16, weight="bold")
    fig.text(0.675, 0.19, "PPDF / system matrix", color=GREEN, fontsize=16, weight="bold")
    fig.text(0.055, 0.10, "All three views are from existing OneCube output files; no values are fabricated for this deck.", color=MUTED, fontsize=12)
    slide_paths.append(SLIDES / "slide_04_onecube_results.png"); savefig(fig, slide_paths[-1])

    # 5
    fig = slide_base(5, "Transition: one cube → full MagicCube", "04 • SCALE THE SAME PIPELINE")
    image_panel(fig, FIG / "magiccube_scaling.png", [0.055, 0.27, 0.89, 0.48])
    fig.text(0.10, 0.13, "2048 GAGG", color=CYAN, fontsize=18, weight="bold")
    fig.text(0.31, 0.13, "+", color=MUTED, fontsize=18, weight="bold")
    fig.text(0.37, 0.13, "2048 K9", color=ORANGE, fontsize=18, weight="bold")
    fig.text(0.58, 0.13, "16 layers", color=PURPLE, fontsize=18, weight="bold")
    fig.text(0.77, 0.13, "67.2 × 67.2 × 32 mm", color=GREEN, fontsize=16, weight="bold")
    slide_paths.append(SLIDES / "slide_05_transition.png"); savefig(fig, slide_paths[-1])

    # 6
    fig = slide_base(6, "Full MagicCube geometry", "05 • FROZEN DETECTOR MODEL")
    image_panel(fig, FIG / "magiccube_geometry_3d.png", [0.055, 0.14, 0.58, 0.67])
    text_box(fig, 0.68, 0.55, 0.25, 0.24, "Geometry facts", "• 16 × 16 × 16 lattice\n• 2 mm cube pitch in z\n• 4.2 mm pitch in x / y\n• source-facing face at z = −16 mm", CYAN, 14)
    text_box(fig, 0.68, 0.22, 0.25, 0.23, "Material roles", "GAGG = sensitive detector\nK9 = interleaved proxy / spacer\n\nThe response map below uses canonical GAGG positions only.", ORANGE, 14)
    slide_paths.append(SLIDES / "slide_06_geometry.png"); savefig(fig, slide_paths[-1])

    # 7
    fig = slide_base(7, "Layer / depth structure", "06 • SELF-COLLIMATION CONCEPT")
    image_panel(fig, FIG / "layer_checkerboard_exploded.png", [0.055, 0.24, 0.89, 0.54])
    fig.text(0.055, 0.13, "The checkerboard phase changes with depth, interleaving sensitive GAGG and K9 along the source-to-detector path.", color=WHITE, fontsize=16)
    fig.text(0.055, 0.08, "This is the structural mechanism to test against response anisotropy and depth-dependent sensitivity.", color=MUTED, fontsize=12)
    slide_paths.append(SLIDES / "slide_07_layers.png"); savefig(fig, slide_paths[-1])

    # 8
    fig = slide_base(8, "Validated MagicCube single-source runtime", "07 • VALIDATED 2048 × 1 RESULT")
    text_box(fig, 0.07, 0.48, 0.26, 0.22, "Transport", "Hits\n189,964", ORANGE, 27)
    text_box(fig, 0.37, 0.48, 0.26, 0.22, "Readout", "Singles\n189,844", CYAN, 27)
    text_box(fig, 0.67, 0.48, 0.26, 0.22, "Shape", "2048 × 1\nall detectors populated", GREEN, 20)
    fig.text(0.07, 0.30, "Validated checks: complete shape • count conservation • positive smoke counts • normalization • PPDF • canonical mapping", color=WHITE, fontsize=14)
    fig.text(0.07, 0.21, "MAGICCUBE_2048x1_END_TO_END_PASS", color=GREEN, fontsize=19, weight="bold", family="DejaVu Sans Mono")
    fig.text(0.07, 0.12, "This is the strongest end-to-end evidence in the current project state.", color=MUTED, fontsize=13)
    slide_paths.append(SLIDES / "slide_08_validated_runtime.png"); savefig(fig, slide_paths[-1])

    # 9
    fig = slide_base(9, "Validated detector response visualization", "08 • STRONGEST RESULT")
    image_panel(fig, FIG / "validated_detector_response.png", [0.055, 0.13, 0.60, 0.68])
    text_box(fig, 0.69, 0.52, 0.24, 0.25, "What is shown", "Every canonical GAGG detector position is colored by its actual validated Singles count for the 140 keV point source.", CYAN, 15)
    text_box(fig, 0.69, 0.20, 0.24, 0.23, "Data boundary", "Validated 2048 × 1 runtime\n\nNo full-FOV matrix values are used here.", GREEN, 15)
    slide_paths.append(SLIDES / "slide_09_detector_response.png"); savefig(fig, slide_paths[-1])

    # 10
    fig = slide_base(10, "Layer / depth response", "09 • VALIDATED RESPONSE AGGREGATION")
    image_panel(fig, FIG / "validated_layer_response.png", [0.055, 0.22, 0.89, 0.58])
    fig.text(0.055, 0.13, "Aggregation is performed directly from the validated 2048-element Singles vector and grouped by physical layer k.", color=WHITE, fontsize=15)
    fig.text(0.055, 0.08, "Use this view to decide whether later comparisons should be made layer-by-layer, by depth index, or on the integrated detector response.", color=MUTED, fontsize=11)
    slide_paths.append(SLIDES / "slide_10_layer_response.png"); savefig(fig, slide_paths[-1])

    # 11
    fig = slide_base(11, "Full-FOV production architecture", "10 • FROM ONE SOURCE TO 2,601")
    image_panel(fig, FIG / "full_fov_architecture.png", [0.055, 0.29, 0.89, 0.42])
    text_box(fig, 0.09, 0.12, 0.25, 0.11, "Input", "51 × 51 = 2,601 source positions", CYAN, 13)
    text_box(fig, 0.38, 0.12, 0.25, 0.11, "Per-source output", "one 2048-element response vector", ORANGE, 13)
    text_box(fig, 0.67, 0.12, 0.25, 0.11, "Target", "2048 × 2,601 system matrix", GREEN, 13)
    slide_paths.append(SLIDES / "slide_11_full_fov_architecture.png"); savefig(fig, slide_paths[-1])

    # 12
    fig = slide_base(12, "Current full-FOV run progress", "11 • PARTIAL PRODUCTION")
    image_panel(fig, FIG / "full_fov_progress.png", [0.055, 0.14, 0.57, 0.67])
    text_box(fig, 0.68, 0.53, 0.25, 0.25, "Marker snapshot", f"completed exit 0: {marker_counts['0']}\nexit 1: {marker_counts['1']}\nrunning: {marker_counts['RUNNING']}\nof 2,601 source tasks", ORANGE, 15)
    text_box(fig, 0.68, 0.21, 0.25, 0.23, "Interpretation", "Completion markers show production progress only.\n\nThe final 2048 × 2,601 matrix is not present, so this is not a final scientific result.", RED, 14)
    slide_paths.append(SLIDES / "slide_12_full_fov_progress.png"); savefig(fig, slide_paths[-1])

    # 13
    fig = slide_base(13, "Current status / next steps", "12 • HANDOFF")
    text_box(fig, 0.055, 0.38, 0.27, 0.36, "Completed", "✓ OneCube pipeline\n✓ full MagicCube geometry\n✓ Hits / Singles runtime\n✓ canonical detector mapping\n✓ validated 2048 × 1 matrix", GREEN, 14)
    text_box(fig, 0.365, 0.38, 0.27, 0.36, "Running", "↻ full-FOV 2,601-source production\n\nStatus remains partial until the source responses are assembled and validated into the final matrix.", ORANGE, 13)
    text_box(fig, 0.675, 0.38, 0.27, 0.36, "Next", "→ compare sensitivity / response with paper\n→ validate geometry and material assumptions\n→ assemble final matrix\n→ reconstruct and assess image quality", CYAN, 13)
    fig.text(0.055, 0.23, "Meeting takeaway", color=WHITE, fontsize=16, weight="bold")
    fig.text(0.055, 0.15, "The single-source chain is validated. The remaining milestone is production-scale full-FOV completion and scientific comparison.", color=WHITE, fontsize=18)
    fig.text(0.055, 0.08, "No claim is made here that the full-FOV final matrix is complete.", color=RED, fontsize=13, weight="bold")
    slide_paths.append(SLIDES / "slide_13_status.png"); savefig(fig, slide_paths[-1])
    return slide_paths


def xml_header():
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def build_pptx(slide_paths, out_path: Path):
    # A self-contained OOXML deck: each slide is a high-resolution, meeting-ready PNG.
    ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    ns_p = "http://schemas.openxmlformats.org/presentationml/2006/main"
    ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    media = []
    files = {}
    files["[Content_Types].xml"] = xml_header() + """<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Default Extension=\"png\" ContentType=\"image/png\"/><Override PartName=\"/ppt/presentation.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml\"/><Override PartName=\"/ppt/slideMasters/slideMaster1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml\"/><Override PartName=\"/ppt/slideLayouts/slideLayout1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml\"/><Override PartName=\"/ppt/theme/theme1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.theme+xml\"/>""" + "".join(f"<Override PartName=\"/ppt/slides/slide{i}.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slide+xml\"/>" for i in range(1, len(slide_paths) + 1)) + "</Types>"
    files["_rels/.rels"] = xml_header() + f"<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"ppt/presentation.xml\"/></Relationships>"
    sld_ids = "".join(f"<p:sldId id=\"{255+i}\" r:id=\"rId{i+1}\"/>" for i in range(1, len(slide_paths)+1))
    files["ppt/presentation.xml"] = xml_header() + f"<p:presentation xmlns:a=\"{ns_a}\" xmlns:r=\"{ns_r}\" xmlns:p=\"{ns_p}\"><p:sldMasterIdLst><p:sldMasterId id=\"2147483648\" r:id=\"rId1\"/></p:sldMasterIdLst><p:sldIdLst>{sld_ids}</p:sldIdLst><p:sldSz cx=\"12192000\" cy=\"6858000\" type=\"screen16x9\"/><p:notesSz cx=\"6858000\" cy=\"9144000\"/></p:presentation>"
    files["ppt/_rels/presentation.xml.rels"] = xml_header() + "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster\" Target=\"slideMasters/slideMaster1.xml\"/>" + "".join(f"<Relationship Id=\"rId{i+1}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide\" Target=\"slides/slide{i}.xml\"/>" for i in range(1, len(slide_paths)+1)) + "</Relationships>"
    files["ppt/slideMasters/slideMaster1.xml"] = xml_header() + f"<p:sldMaster xmlns:a=\"{ns_a}\" xmlns:r=\"{ns_r}\" xmlns:p=\"{ns_p}\"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/><a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap accent1=\"accent1\" accent2=\"accent2\" accent3=\"accent3\" accent4=\"accent4\" accent5=\"accent5\" accent6=\"accent6\" bg1=\"lt1\" bg2=\"lt2\" folHlink=\"folHlink\" hlink=\"hlink\" tx1=\"dk1\" tx2=\"dk2\"/><p:sldLayoutIdLst><p:sldLayoutId id=\"1\" r:id=\"rId1\"/></p:sldLayoutIdLst></p:sldMaster>"
    files["ppt/slideMasters/_rels/slideMaster1.xml.rels"] = xml_header() + "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout1.xml\"/></Relationships>"
    files["ppt/slideLayouts/slideLayout1.xml"] = xml_header() + f"<p:sldLayout xmlns:a=\"{ns_a}\" xmlns:r=\"{ns_r}\" xmlns:p=\"{ns_p}\" type=\"blank\"><p:cSld name=\"Blank\"><p:spTree><p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>"
    files["ppt/slideLayouts/_rels/slideLayout1.xml.rels"] = xml_header() + "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster\" Target=\"../slideMasters/slideMaster1.xml\"/></Relationships>"
    files["ppt/theme/theme1.xml"] = xml_header() + f"<a:theme xmlns:a=\"{ns_a}\" name=\"Meeting Theme\"><a:themeElements><a:clrScheme name=\"Default\"><a:dk1><a:srgbClr val=\"000000\"/></a:dk1><a:lt1><a:srgbClr val=\"FFFFFF\"/></a:lt1><a:dk2><a:srgbClr val=\"1F2937\"/></a:dk2><a:lt2><a:srgbClr val=\"F3F4F6\"/></a:lt2><a:accent1><a:srgbClr val=\"58D7FF\"/></a:accent1><a:accent2><a:srgbClr val=\"FFB86B\"/></a:accent2><a:accent3><a:srgbClr val=\"39D98A\"/></a:accent3><a:accent4><a:srgbClr val=\"B9A0FF\"/></a:accent4><a:accent5><a:srgbClr val=\"FF6B6B\"/></a:accent5><a:accent6><a:srgbClr val=\"A7B7C9\"/></a:accent6><a:hlink><a:srgbClr val=\"58D7FF\"/></a:hlink><a:folHlink><a:srgbClr val=\"B9A0FF\"/></a:folHlink></a:clrScheme><a:fontScheme name=\"Default\"><a:majorFont><a:latin typeface=\"Aptos Display\"/></a:majorFont><a:minorFont><a:latin typeface=\"Aptos\"/></a:minorFont></a:fontScheme><a:fmtScheme name=\"Default\"><a:fillStyleLst/><a:lnStyleLst/><a:effectStyleLst/><a:bgFillStyleLst/></a:fmtScheme></a:themeElements></a:theme>"
    for i, slide_path in enumerate(slide_paths, 1):
        rid_img = "rId1"; rid_layout = "rId2"
        files[f"ppt/slides/slide{i}.xml"] = xml_header() + f"<p:sld xmlns:a=\"{ns_a}\" xmlns:r=\"{ns_r}\" xmlns:p=\"{ns_p}\"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/><p:pic><p:nvPicPr><p:cNvPr id=\"2\" name=\"Slide image\"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed=\"{rid_img}\"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"12192000\" cy=\"6858000\"/></a:xfrm><a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom></p:spPr></p:pic></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"
        files[f"ppt/slides/_rels/slide{i}.xml.rels"] = xml_header() + f"<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"{rid_img}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/image\" Target=\"../media/image{i}.png\"/><Relationship Id=\"{rid_layout}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout1.xml\"/></Relationships>"
        media.append((f"ppt/media/image{i}.png", slide_path.read_bytes()))
    files["docProps/core.xml"] = xml_header() + "<cp:coreProperties xmlns:cp=\"http://schemas.openxmlformats.org/package/2006/metadata/core-properties\" xmlns:dc=\"http://purl.org/dc/elements/1.1/\"><dc:title>MagicCube Meeting Update</dc:title><dc:subject>OneCube to full MagicCube progress</dc:subject><dc:creator>MagicCube project</dc:creator></cp:coreProperties>"
    files["docProps/app.xml"] = xml_header() + "<Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties\"><Application>MagicCube meeting deck generator</Application><PresentationFormat>Widescreen</PresentationFormat></Properties>"
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items(): z.writestr(name, data)
        for name, data in media: z.writestr(name, data)


def write_markdown(marker_counts, slide_paths):
    md = ["# MagicCube meeting update", "", "A meeting-ready progress deck from OneCube to full MagicCube.", "", "## Evidence boundary", "", "- OneCube and the MagicCube 2048×1 result use existing validated outputs.", "- The full-FOV run is shown only through completion markers. The final 2048×2601 matrix is not present and is not claimed as complete.", "- The geometry figures use the frozen MagicCube configuration and canonical detector map.", ""]
    slides = [
        ("1. Title / objective", "Goal: reproduce the Magic-Cube self-collimating gamma camera in GATE/mcsim. Progression: OneCube → MagicCube → full-FOV production.", "Configuration and project status."),
        ("2. OneCube motivation", "One 2×2×2 mm GAGG cube plus a 140 keV point source provides the smallest useful proof that the transport-to-matrix pipeline works.", "Validated OneCube geometry and source configuration."),
        ("3. OneCube end-to-end pipeline", "Source → GATE → Hits → Singles → PPDF → 1×1 system matrix. PASS: 233 Hits, 233 Singles, ppdf=1.0.", "OneCube final_validation.json, system_matrix.csv, ppdf.csv."),
        ("4. OneCube visual results", "Geometry, Hits/Singles positions, and response dashboard are copied from existing OneCube visualization outputs.", "Existing OneCube PNG outputs."),
        ("5. Transition to full MagicCube", "Scale to 2048 GAGG + 2048 K9 over 16 layers while preserving the same pipeline.", "Frozen magiccube_config.json."),
        ("6. Full MagicCube geometry", "Clean 3D render of the 16×16×16 checkerboard lattice with GAGG/K9 roles, source-facing side, axes, and dimensions.", "Frozen configuration plus detector_map.csv."),
        ("7. Layer / checkerboard structure", "Representative depth layers show the phase-alternating GAGG/K9 checkerboard that makes self-collimation testable.", "Frozen material rule (ix+iy+k) mod 2."),
        ("8. Validated MagicCube single-source runtime", "Validated 2048×1 run: 189,964 Hits, 189,844 Singles, complete 2048-vector, and MAGICCUBE_2048x1_END_TO_END_PASS.", "final_summary_validation.json, runtime_validation_validation.json, merge_summary.json, raw system matrix."),
        ("9. Validated detector response", "Actual Singles counts color all 2048 canonical GAGG positions for the validated point source.", "system_matrix_raw.npy plus detector_map.csv."),
        ("10. Layer / depth response", "Actual validated Singles counts aggregated by physical layer k, with representative layer heatmaps.", "system_matrix_raw.npy plus detector_map.csv."),
        ("11. Full-FOV production architecture", "2,601 source positions each produce a 2048-element vector; columns assemble into a 2048×2,601 matrix.", "source_grid_config.json and production architecture."),
        ("12. Current full-FOV run progress", f"Marker snapshot: exit 0={marker_counts['0']}, exit 1={marker_counts['1']}, running={marker_counts['RUNNING']}. PARTIAL PRODUCTION — NOT FINAL SCIENTIFIC RESULT.", "runtime/merged/full/task_*.exit_code.txt markers only; no final matrix values."),
        ("13. Current status / next steps", "OneCube, geometry, Hits/Singles, mapping, and 2048×1 validation are complete. Full-FOV production is ongoing; next steps are comparison, assumptions validation, final matrix, and reconstruction.", "Mixed validated and partial-production status."),
    ]
    for i, (title, message, provenance) in enumerate(slides, 1):
        md += [f"## {title}", "", message, "", f"**Data status:** {provenance}", "", f"![Slide {i:02d}](slides/{slide_paths[i-1].name})", ""]
    (OUT / "MagicCube_Meeting_Update.md").write_text("\n".join(md))


def write_summary(marker_counts, slide_paths):
    artifact_lines = []
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name != "SLIDE_GENERATION_SUMMARY.md":
            artifact_lines.append(f"- `{p.relative_to(OUT)}` — {p.stat().st_size:,} bytes")
    text = f"""# Slide generation summary

Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}

## Scope and safety

- All generated artifacts are under `MagicCubeFinal/meeting_slides/`.
- Gate executed: **NO**.
- Slurm submitted: **NO**.
- Current production jobs stopped: **NO**.
- Simulation code, configuration, detector map, GATE macros, Slurm scripts, runtime data, and production jobs were not modified by this generation step.
- The full-FOV final matrix is not present; it is not claimed complete.

## Data provenance

### Validated data used

- OneCube: `OneCube/results/validation/final_validation.json`, `OneCube/results/system_matrix/system_matrix.csv`, `OneCube/results/ppdf/ppdf.csv`, and existing visualization PNGs.
- MagicCube single-source: `MagicCubeFinal/results/final_summary_validation.json`, `results/validation/runtime_validation_validation.json`, `runtime/merged/merge_summary.json`, `results/system_matrix/system_matrix_raw.npy`, `results/system_matrix/system_matrix.npy`, and `config/detector_map.csv`.
- Geometry / source grid: frozen `config/magiccube_config.json` and `config/source_grid_config.json`.

### Partial production data used

- Slide 12 uses only existing `runtime/sim/full/task_*.exit_code.txt` completion markers.
- Marker snapshot at generation time: exit 0 completed = **{marker_counts['0']}**, exit 1 = **{marker_counts['1']}**, RUNNING = **{marker_counts['RUNNING']}**, total marker files = **{sum(marker_counts.values()) - marker_counts['other']}**.
- Because failed/running tasks and the absent assembled matrix remain, the slide is labeled **PARTIAL PRODUCTION — NOT FINAL SCIENTIFIC RESULT**.

## Slide status

| Slides | Status |
|---|---|
| 1–7 | Project objective, validated OneCube evidence, frozen geometry/configuration, and structural illustrations |
| 8–10 | **Validated MagicCube 2048×1 data** |
| 11 | Architecture / target-shape explanation |
| 12 | **Partial production markers only** |
| 13 | Mixed completed + partial status and next steps |

## Generated artifacts

{chr(10).join(artifact_lines)}

## Verification intent

- PNGs are checked for existence and non-zero size after generation.
- The PPTX is checked as a readable ZIP package containing 13 slide XML parts and 13 slide PNG media parts.
- The Markdown backup is checked for existence and non-zero size.
- No Gate or Slurm command is invoked by `generate_meeting_slides.py`.
"""
    (OUT / "SLIDE_GENERATION_SUMMARY.md").write_text(text)


def main():
    dm, raw, response, cfg, marker_counts = make_assets()
    slides = make_slides(dm, raw, response, cfg, marker_counts)
    pptx = OUT / "MagicCube_Meeting_Update.pptx"
    build_pptx(slides, pptx)
    write_markdown(marker_counts, slides)
    write_summary(marker_counts, slides)
    # Final local checks for the generation step.
    pngs = list(OUT.rglob("*.png"))
    assert len(pngs) >= 13
    assert all(p.stat().st_size > 0 for p in pngs)
    assert pptx.exists() and pptx.stat().st_size > 0
    assert (OUT / "MagicCube_Meeting_Update.md").stat().st_size > 0
    with zipfile.ZipFile(pptx) as z:
        names = set(z.namelist())
        assert "ppt/presentation.xml" in names
        assert sum(n.startswith("ppt/slides/slide") and n.endswith(".xml") for n in names) == 13
        assert sum(n.startswith("ppt/media/image") and n.endswith(".png") for n in names) == 13
    print(json.dumps({"output": str(OUT), "png_count": len(pngs), "pptx_bytes": pptx.stat().st_size, "marker_counts": marker_counts}, indent=2))


if __name__ == "__main__":
    main()
