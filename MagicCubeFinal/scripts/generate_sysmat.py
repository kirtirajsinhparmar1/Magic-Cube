#!/usr/bin/env python3
"""Write complete canonical 2048-by-N raw and exposure-normalized system matrices."""
import sys

import numpy as np

from generate_ppdf import response_table
from inspect_root import PROJECT_ROOT, write_json, write_table, stage_arguments


def main():
    stage_arguments(__doc__)
    frame, sources = response_table()
    frame['cps_per_bq'] = frame.raw_singles_count / (frame.activity_bq * frame.acquisition_s)
    frame['cps_per_mbq'] = frame.cps_per_bq * 1e6
    out = PROJECT_ROOT / 'results' / 'system_matrix'
    columns = ['detector_id', 'source_id', 'source_x_mm', 'source_y_mm', 'source_z_mm',
               'raw_singles_count', 'acquisition_s', 'activity_bq', 'cps_per_bq', 'cps_per_mbq']
    parquet = write_table(frame[columns], out / 'system_matrix')
    shape = (2048, len(sources))
    raw = frame.raw_singles_count.to_numpy(dtype=np.int64).reshape(shape)
    normalized = frame.cps_per_bq.to_numpy(dtype=np.float64).reshape(shape)
    np.save(out / 'system_matrix_raw.npy', raw)
    np.save(out / 'system_matrix_raw_counts.npy', raw)
    np.save(out / 'system_matrix.npy', normalized)
    np.save(out / 'system_matrix_cps_per_bq.npy', normalized)
    write_json(out / 'system_matrix_metadata.json', {'shape': list(shape),
               'detector_ids': list(range(2048)), 'source_ids': sources.source_id.astype(int).tolist(),
               'normalization': 'summed replicate counts / (activity_bq * summed replicate acquisition_s)',
               'npy_quantity': 'cps_per_bq', 'raw_count_preserved': True, 'parquet_written': parquet})
    print(f'System matrix: {shape}, raw count {int(raw.sum())}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(f'System-matrix generation failed: {error}', file=sys.stderr)
        sys.exit(1)
