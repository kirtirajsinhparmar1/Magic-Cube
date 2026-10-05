#!/usr/bin/env python3
"""Plot the full response heatmap and a selected detector's PPDF."""
import sys

import numpy as np
import pandas as pd

from inspect_root import PROJECT_ROOT, stage_arguments


def main():
    args = stage_arguments(__doc__, lambda parser: parser.add_argument('--detector-id', type=int, default=0))
    if not 0 <= args.detector_id < 2048:
        raise ValueError('Selected detector ID must be in 0..2047')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matrix = np.load(PROJECT_ROOT / 'results' / 'system_matrix' / 'system_matrix.npy', allow_pickle=False)
    ppdf = pd.read_csv(PROJECT_ROOT / 'results' / 'ppdf' / 'ppdf.csv')
    selected = ppdf[ppdf.detector_id == args.detector_id].sort_values('source_id')
    if matrix.ndim != 2 or matrix.shape[0] != 2048 or selected.empty:
        raise ValueError('Matrix or selected detector PPDF has invalid dimensions')
    out = PROJECT_ROOT / 'results' / 'plots'
    out.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 7))
    im = ax.imshow(matrix, aspect='auto', origin='lower', interpolation='nearest')
    ax.set(xlabel='Source column (ascending source_id)', ylabel='Canonical detector_id', title='System response (cps/Bq)')
    fig.colorbar(im, ax=ax, label='cps/Bq')
    fig.tight_layout()
    fig.savefig(out / 'system_matrix_heatmap.png', dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(selected.source_id, selected.ppdf, marker='.', linewidth=1)
    ax.set(xlabel='source_id', ylabel='PPDF', title=f'Detector {args.detector_id} response distribution')
    fig.tight_layout()
    fig.savefig(out / f'ppdf_detector_{args.detector_id}.png', dpi=180)
    plt.close(fig)
    # Coordinates can span several z planes; show each plane without collapsing
    # distinct source positions into an x/y cell.
    planes = sorted(selected.source_z_mm.unique())
    columns = min(3, len(planes))
    rows = (len(planes) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(5 * columns, 4 * rows), squeeze=False)
    vmax = float(selected.ppdf.max()) or 1.0
    for ax, z in zip(axes.flat, planes):
        plane = selected[selected.source_z_mm == z]
        xs, ys = sorted(plane.source_x_mm.unique()), sorted(plane.source_y_mm.unique())
        rectangular = len(plane) == len(xs) * len(ys) and not plane[['source_x_mm', 'source_y_mm']].duplicated().any()
        if rectangular and len(xs) > 1 and len(ys) > 1:
            grid = plane.pivot(index='source_y_mm', columns='source_x_mm', values='ppdf').reindex(index=ys, columns=xs)
            artist = ax.pcolormesh(xs, ys, grid.to_numpy(), shading='nearest', vmin=0, vmax=vmax)
        else:
            artist = ax.scatter(plane.source_x_mm, plane.source_y_mm, c=plane.ppdf, s=55,
                                marker='s', vmin=0, vmax=vmax)
        ax.set(xlabel='Source x (mm)', ylabel='Source y (mm)', title=f'z = {z:g} mm')
        ax.set_aspect('equal', adjustable='box')
        fig.colorbar(artist, ax=ax, label='Detector-conditioned PPDF')
    for ax in list(axes.flat)[len(planes):]:
        ax.set_visible(False)
    fig.suptitle(f'PPDF of canonical detector {args.detector_id}')
    fig.tight_layout()
    fig.savefig(out / f'PPDF_Detector_{args.detector_id}.png', dpi=180)
    plt.close(fig)
    print(f'Plots written to {out}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(f'System-matrix plotting failed: {error}', file=sys.stderr)
        sys.exit(1)
