"""Independently replay retained count dictionaries into benchmark magnitudes.

This verifier deliberately does not call either detector's reconstruction code.
It decodes register bits, assigns neighbor destinations and calibrates the three
operators directly from their measurement laws.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np


def replay(records, method, shape=(128, 128), tile_size=16):
    n_pos = (tile_size * tile_size).bit_length() - 1
    core = tile_size - 2
    components = {key: np.zeros(shape) for key in ('horizontal', 'vertical')}
    for record in records:
        direction = record['direction']
        stride = 1 if direction == 'horizontal' else tile_size
        probabilities = np.zeros((tile_size, tile_size))
        total = sum(record['counts'].values())
        for key, count in record['counts'].items():
            position = int(key.replace(' ', ''), 2) & ((1 << n_pos) - 1)
            if not position & stride:
                continue
            pair_base = position & ~stride
            coordinate = pair_base % tile_size if direction == 'horizontal' else pair_base // tile_size
            destination = (coordinate + 1 - record['pair_offset']) % tile_size
            if destination == 0:
                continue
            flat = pair_base + (destination - coordinate) * stride
            probabilities.flat[flat] += count / total
        y, x = record['tile_y'], record['tile_x']
        if direction == 'horizontal' and x == 0:
            probabilities[:, 1] = 0
        if direction == 'vertical' and y == 0:
            probabilities[1, :] = 0
        h, w = min(core, shape[0] - y), min(core, shape[1] - x)
        p = probabilities[1:1+h, 1:1+w]
        if method == 'QPIE':
            square = 2 * record['preparation_norm_squared'] * p
        elif method == 'FRQI':
            square = (1020 / np.pi * np.arcsin(np.sqrt(np.clip(tile_size**2 * p, 0, 1) / 2))) ** 2
        elif method == 'NEQR':
            square = tile_size**2 * p
        else:
            raise ValueError('Unknown method')
        target = components[direction][y:y+h, x:x+w]
        np.maximum(target, square, out=target)
    return np.sqrt(components['horizontal'] + components['vertical'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'results/encoding_benchmark')
    args = parser.parse_args()
    results = sorted((args.output / 'runs').glob('*/result.json'))
    if len(results) != 144:
        raise ValueError('Expected exactly 144 completed quantum results')
    maximum_error, circuits, shots = 0.0, 0, 0
    for path in results:
        info = json.loads(path.read_text())
        with gzip.open(path.parent / 'counts.jsonl.gz', 'rt', encoding='utf-8') as handle:
            records = [json.loads(line) for line in handle]
        magnitude = replay(records, info['metrics']['method'])
        saved = np.load(path.parent / 'maps.npz')
        error = float(np.max(np.abs(magnitude - saved['magnitude'])))
        maximum_error = max(maximum_error, error)
        np.testing.assert_allclose(magnitude, saved['magnitude'], rtol=1e-12, atol=1e-12)
        strength = magnitude / magnitude.max() if magnitude.max() else magnitude
        np.testing.assert_allclose(strength, saved['strength'], rtol=1e-12, atol=1e-12)
        circuits += len(records)
        shots += sum(sum(r['counts'].values()) for r in records)
    report = {'status': 'passed', 'quantum_runs_replayed': len(results),
              'circuits_replayed': circuits, 'measurement_shots_replayed': shots,
              'maximum_absolute_magnitude_error': maximum_error,
              'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'independence': 'Direct bit decoding and calibration; imports no project detector or reconstruction code'}
    (args.output / 'count_replay_verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
