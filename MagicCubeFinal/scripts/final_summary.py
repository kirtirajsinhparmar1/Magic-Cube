#!/usr/bin/env python3
"""Report persisted validation evidence without manufacturing runtime success."""
import json
import sys

from inspect_root import PROJECT_ROOT, stage_arguments, write_json


def main():
    args = stage_arguments(__doc__, lambda parser: parser.add_argument('--mode', choices=['validation', 'full'], default='validation'))
    path = PROJECT_ROOT / 'results' / 'validation' / f'runtime_validation_{args.mode}.json'
    if not path.is_file():
        raise ValueError(f'Runtime validation evidence missing: {path}')
    validation = json.loads(path.read_text())
    metadata = json.loads((PROJECT_ROOT / 'results' / 'system_matrix' / 'system_matrix_metadata.json').read_text())
    summary = {'mode': args.mode, 'shape': metadata['shape'], 'passed': validation['passed'],
               'pass_token': validation.get('pass_token'), 'validation_report': str(path),
               'raw_counts': 'results/system_matrix/system_matrix_raw.npy',
               'normalized_response': 'results/system_matrix/system_matrix.npy',
               'canonical_detector_order': '0..2047', 'source_order': metadata['source_ids'],
               'failures': validation['failures']}
    write_json(PROJECT_ROOT / 'results' / f'final_summary_{args.mode}.json', summary)
    print(json.dumps(summary, indent=2))
    return 0 if validation['passed'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(f'Final summary failed: {error}', file=sys.stderr)
        sys.exit(1)
