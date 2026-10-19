#!/usr/bin/env python3
"""Full-grid scientific plots; heatmap selection never changes simulation coverage."""
import argparse

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from production_common import ROOT, MATRIX, PPDF, PLOTS, full_inputs, require, verify_provenance


def save(fig, name):
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOTS / name, dpi=120, bbox_inches='tight')
    plt.close(fig)


def spatial_panel(ax, sources, values, title, detector=None):
    frame = sources[['x_mm', 'y_mm']].copy()
    frame['value'] = values
    image = frame.pivot(index='y_mm', columns='x_mm', values='value')
    xs, ys = image.columns.to_numpy(), image.index.to_numpy()
    dx = float(xs[1] - xs[0]) if len(xs) > 1 else 1.0
    dy = float(ys[1] - ys[0]) if len(ys) > 1 else 1.0
    artist = ax.imshow(image.to_numpy(), origin='lower', interpolation='nearest', aspect='equal',
                       extent=(xs.min() - dx / 2, xs.max() + dx / 2, ys.min() - dy / 2, ys.max() + dy / 2))
    if detector is not None:
        ax.plot(detector.x_mm, detector.y_mm, '+', color='white', markersize=8, label='detector x/y projection')
        ax.legend(fontsize='small')
    ax.set(xlabel='source x (mm)', ylabel='source y (mm)', title=title)
    ax.figure.colorbar(artist, ax=ax, shrink=0.8)


def detector_heatmap(detector_id, sources, mapping, response, ppdf):
    require(detector_id in mapping.detector_id.to_numpy(), 'Selected detector ID outside canonical map')
    row = mapping.loc[mapping.detector_id == detector_id].iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    spatial_panel(axes[0], sources, ppdf[detector_id], f'Detector {detector_id}: PPDF', row)
    spatial_panel(axes[1], sources, response[detector_id] * 1e6, f'Detector {detector_id}: cps/MBq', row)
    save(fig, f'PPDF_Detector_{detector_id}.png')


def global_plots(detector_id, sources, mapping, raw, response, ppdf):
    row = mapping.loc[mapping.detector_id == detector_id].iloc[0]
    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(121, projection='3d')
    ax.scatter(mapping.x_mm, mapping.y_mm, mapping.z_mm, s=2, alpha=0.25, label='GAGG detectors')
    ax.scatter(sources.x_mm, sources.y_mm, sources.z_mm, c=ppdf[detector_id], s=3, label='full source plane')
    ax.scatter([row.x_mm], [row.y_mm], [row.z_mm], c='red', s=45, label=f'detector {detector_id}')
    ax.set(xlabel='x (mm)', ylabel='y (mm)', zlabel='z (mm)', title='Detector and full source plane')
    ax.legend(fontsize='small')
    spatial_panel(fig.add_subplot(122), sources, ppdf[detector_id], f'PPDF support: detector {detector_id}', row)
    save(fig, 'positions.png')

    fig, ax = plt.subplots(figsize=(9, 5))
    artist = ax.imshow(response, aspect='auto', interpolation='nearest', origin='lower')
    ax.set(xlabel='source column (deterministic source ID order)', ylabel='canonical detector ID', title='Absolute response: counts / second / Bq')
    fig.colorbar(artist, ax=ax)
    save(fig, 'system_matrix_heatmap.png')

    # Visualize the validated conceptual centers, without constructing new GATE geometry.
    axes = [np.sort(mapping[f'{a}_mm'].unique()) for a in 'xyz']
    ix, iy, iz = np.meshgrid(*(np.arange(len(axis)) for axis in axes), indexing='ij')
    centers = np.column_stack([axes[0][ix.ravel()], axes[1][iy.ravel()], axes[2][iz.ravel()]])
    sensitive = ((ix + iy + iz).ravel() % 2 == 0)
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection='3d')
    for mask, color, label in ((sensitive, 'green', 'GAGG'), (~sensitive, 'skyblue', 'K9 proxy')):
        ax.scatter(*centers[mask].T, s=4, alpha=0.35, c=color, label=label)
    ax.set(xlabel='x (mm)', ylabel='y (mm)', zlabel='z (mm)', title='Full material-center arrangement')
    ax.legend()
    save(fig, 'detector_geometry.png')

    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection='3d')
    artist = ax.scatter(mapping.x_mm, mapping.y_mm, mapping.z_mm, c=mapping.detector_id, s=5)
    ax.set(xlabel='x (mm)', ylabel='y (mm)', zlabel='z (mm)', title='Canonical detector ID layout')
    fig.colorbar(artist, ax=ax, label='detector ID', shrink=0.6)
    save(fig, 'detector_id_layout.png')

    fig, ax = plt.subplots(figsize=(6, 5))
    artist = ax.scatter(sources.x_mm, sources.y_mm, c=sources.source_id, s=5)
    ax.set(xlabel='source x (mm)', ylabel='source y (mm)', title=f'Full grid at z={sources.z_mm.iloc[0]:g} mm', aspect='equal')
    fig.colorbar(artist, ax=ax, label='source ID')
    save(fig, 'source_grid.png')

    fig, ax = plt.subplots(figsize=(6, 5))
    spatial_panel(ax, sources, response.sum(axis=0) * 1e6, 'Sensitivity (cps/MBq)')
    save(fig, 'sensitivity_map.png')

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(mapping.detector_id, raw.sum(axis=1), linewidth=0.7)
    ax.set(xlabel='canonical detector ID', ylabel='raw Singles across FOV', title='Detector-response summary')
    save(fig, 'detector_response_summary.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--global', dest='global_plots', action='store_true')
    parser.add_argument('--detector-id', type=int, default=0)
    parser.add_argument('--plot-index', type=int)
    args = parser.parse_args()
    sources, _, mapping = full_inputs()
    verify_provenance()
    detector_id = args.detector_id
    if args.plot_index is not None:
        manifest = pd.read_csv(ROOT / 'runtime/manifests/plot_manifest_full.csv')
        require(0 <= args.plot_index < len(manifest), 'Plot array index outside manifest')
        detector_id = int(manifest.iloc[args.plot_index].detector_id)
    require(detector_id in mapping.detector_id.to_numpy(), 'Invalid detector ID')
    raw = np.load(MATRIX / 'system_matrix_raw.npy', mmap_mode='r', allow_pickle=False)
    response = np.load(MATRIX / 'system_matrix.npy', mmap_mode='r', allow_pickle=False)
    ppdf = np.load(PPDF / 'ppdf.npy', mmap_mode='r', allow_pickle=False)
    require(raw.shape == response.shape == ppdf.shape == (len(mapping), len(sources)), 'Plot matrix shape mismatch')
    if args.global_plots:
        global_plots(detector_id, sources, mapping, raw, response, ppdf)
    else:
        detector_heatmap(detector_id, sources, mapping, response, ppdf)
    print(f'Full-grid plots written to {PLOTS}')


if __name__ == '__main__':
    main()
