#!/usr/bin/env python3
"""Plot canonical detector and manifest source positions without needing GATE outputs."""
import sys

from inspect_root import PROJECT_ROOT, detector_map, source_manifest, stage_arguments


def main():
    args = stage_arguments(__doc__, lambda parser: parser.add_argument('--detector-id', type=int, default=0))
    if not 0 <= args.detector_id < 2048:
        raise ValueError('Selected detector ID must be in 0..2047')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    detectors = detector_map()
    sources = source_manifest().drop_duplicates('source_id')
    out = PROJECT_ROOT / 'results' / 'plots'
    out.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(9, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(detectors.x_mm, detectors.y_mm, detectors.z_mm, s=3, alpha=.4, label='2048 detector centers')
    ax.scatter(sources.source_x_mm, sources.source_y_mm, sources.source_z_mm, c='red', s=20, label='Source positions')
    selected = detectors[detectors.detector_id == args.detector_id].iloc[0]
    ax.scatter([selected.x_mm], [selected.y_mm], [selected.z_mm], c='black', s=40,
               label=f'Selected detector {args.detector_id}')
    ax.set(xlabel='x (mm)', ylabel='y (mm)', zlabel='z (mm)', title='Canonical detector and source positions')
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / 'positions.png', dpi=180)
    plt.close(fig)
    print(out / 'positions.png')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(f'Position plotting failed: {error}', file=sys.stderr)
        sys.exit(1)
