#!/usr/bin/env python3
"""Compute all-detector PPDF directly from the compact raw matrix, without rereading events."""
import numpy as np

from production_common import MATRIX, PPDF, full_inputs, verify_provenance, require, write_json, write_long_parquet


def main():
    sources, _, mapping = full_inputs()
    fingerprint = verify_provenance()
    raw = np.load(MATRIX / 'system_matrix_raw.npy', mmap_mode='r', allow_pickle=False)
    require(raw.shape == (len(mapping), len(sources)), 'Raw matrix dimensions mismatch')
    totals = raw.sum(axis=1)
    ppdf = np.divide(raw, totals[:, None], out=np.zeros(raw.shape, dtype=float), where=totals[:, None] > 0)
    PPDF.mkdir(parents=True, exist_ok=True)
    np.save(PPDF / 'ppdf.npy', ppdf, allow_pickle=False)
    write_long_parquet(PPDF / 'ppdf.parquet', raw, sources, ppdf, 'ppdf')
    write_json(PPDF / 'ppdf_metadata.json', {'shape': list(ppdf.shape), 'fingerprint': fingerprint,
                'detector_ids': mapping.detector_id.tolist(), 'source_ids': sources.source_id.tolist(),
                'formula': 'n_ij / sum_j(n_ij)', 'zero_response_detector_ids': mapping.detector_id[totals == 0].tolist(),
                'raw_counts_preserved': True, 'long_format_order': 'source outer, detector inner'})
    print(f'PPDF prepared: {ppdf.shape}; zero-response rows remain zero')


if __name__ == '__main__':
    main()
