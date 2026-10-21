"""Reproducible crop-scale SomBench test benchmark of actual measured encodings.

Run from this repository: python experiments/benchmark_encodings.py
Workers import the existing detectors; no analytical shortcut supplies their output.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
NEQR_ROOT = ROOT.parent / 'Quantum_Lunar_Edge_Detection_NEQR'
REVISION = '20f800becb64a0c7ad314652a683f97f0281fe67'
DEFAULT_OUTPUT = ROOT / 'results/encoding_benchmark'
METHODS = ('QPIE', 'FRQI', 'NEQR')
SEEDS = (42, 43, 44)
BUDGETS = (1024, 8192)
METRICS = ('f1_exact', 'f1_1px', 'f1_2px', 'pr_auc', 'iou', 'coverage',
           'operator_rmse', 'elapsed_seconds')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.part')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def source_hashes():
    files = ('quantum/variant_circuit.py', 'quantum/full_image.py',
             'quantum/qpie_full_image.py', 'quantum/qhed_circuit.py',
             'quantum/simulation.py', 'quantum/reconstruction.py',
             'preprocessing/real_image.py', 'preprocessing/annotation_rasteriser.py',
             'evaluation/metrics.py', 'classical/sobel.py', 'classical/canny.py',
             'classical/robinson_compass.py')
    return {f'{repo.name}/{file}': digest(repo / file)
            for repo in (ROOT, NEQR_ROOT) for file in files}


def select_rows(rows, prior_stems, count=8):
    """Select without labels, excluding prior products and repeating none."""
    excluded = {stem.split('_r')[0] for stem in prior_stems}
    eligible = [(index, row) for index, row in enumerate(rows)
                if str(row['DATASET']).lower() == 'test'
                and row['PRODUCT_ID'] not in excluded]
    eligible.sort(key=lambda item: hashlib.sha256(
        ('20261019:' + str(item[1]['WAC_VIS_TILE'])).encode()).hexdigest())
    chosen, products = [], set()
    for index, row in eligible:
        if row['PRODUCT_ID'] not in products:
            chosen.append({'metadata_row_index': index, 'metadata': row,
                           'stem': Path(row['WAC_VIS_TILE']).stem})
            products.add(row['PRODUCT_ID'])
        if len(chosen) == count:
            return chosen
    raise ValueError('Not enough eligible independent product IDs')


def prepare(output):
    import numpy as np
    import pyarrow.parquet as pq
    import ijson
    from PIL import Image
    from data.sombench.fetch_case import download
    from preprocessing.real_image import load_real_tiff
    from preprocessing.annotation_rasteriser import rasterise_image_annotations

    base = ('https://huggingface.co/datasets/nasa-ibm-ai4science/'
            f'Sombench-WAC-Crater-Detection/resolve/{REVISION}/')
    cache = ROOT / 'data/sombench/cache' / REVISION
    metadata_path = download(base + 'metadata.parquet', cache / 'metadata.parquet')
    previous = ROOT / 'data/sombench/selected_30_images.csv'
    with previous.open(newline='') as handle:
        prior_stems = [r['stem'] for r in csv.DictReader(handle)]
    cases = select_rows(pq.read_table(metadata_path).to_pylist(), prior_stems)
    protocol = {
        'schema': 1, 'dataset': 'nasa-ibm-ai4science/Sombench-WAC-Crater-Detection',
        'revision': REVISION, 'split': 'test', 'selection_seed': '20261019',
        'selection': 'SHA256-ranked metadata tile names; 8 distinct products; exclude all prior selected30 product IDs',
        'excluded_stems': prior_stems, 'prior_selection_sha256': digest(previous),
        'cases': cases, 'crop': {'size': 128, 'position': 'center', 'native_resolution': True},
        'preprocessing': 'Mean bands; full-tile global 2-98 percentile scaling; no smoothing; fixed center crop',
        'seeds': list(SEEDS), 'shots_per_circuit': list(BUDGETS), 'tile_size': 16,
        'batch_tiles': 16, 'subtract_tile_min': False, 'rim_width': 1,
        'threshold': 'Same float Otsu for continuous maps; Canny retains automatic median thresholds',
        'evaluation_border': 2, 'aggregation': 'Average seeds within image, then macro-average images',
        'bootstrap': '10000 paired image resamples, seed20261019, percentile95; exploratory, no multiplicity correction',
        'timing': 'Detector calls including count-audit writes; no trace capture; excludes imports, preprocessing and metrics; not hardware timing',
        'label_limit': 'Catalog-derived approximate rims, not pixel-perfect edges',
        'scope': 'Eight native128 center crops from test partition; not full-image or proven geographically independent benchmark',
        'license': 'CC-BY-4.0', 'attribution': 'NASA-IBM AI4Science SomBench; Robbins (2019) crater catalog',
        'source_hashes': source_hashes(), 'benchmark_script_sha256': digest(__file__),
    }
    protocol_path = output / 'protocol.json'
    if protocol_path.exists() and json.loads(protocol_path.read_text()) != protocol:
        raise ValueError('Existing protocol differs; use a new output directory')
    # Freeze case selection and all settings before opening annotation labels.
    write_json(protocol_path, protocol)
    print('Protocol frozen before annotations: 8 test products, 128px center crops', flush=True)
    annotation_path = download(base + 'test.json', cache / 'test.json')
    wanted = {case['stem'] for case in cases}
    with annotation_path.open('rb') as handle:
        info = {Path(item['file_name']).stem: item
                for item in ijson.items(handle, 'images.item', use_float=True)
                if Path(item['file_name']).stem in wanted}
    if set(info) != wanted:
        raise ValueError('Selected metadata not present in test annotation split')
    selected_ids = {item['id'] for item in info.values()}
    with annotation_path.open('rb') as handle:
        annotations = [ann for ann in ijson.items(handle, 'annotations.item', use_float=True)
                       if ann['image_id'] in selected_ids]
    records = []
    for case in cases:
        stem = case['stem']
        print('Preparing ' + stem, flush=True)
        image_path = download(base + 'images_tiff/' + stem + '.tif', cache / (stem + '.tif'))
        image, valid, loading = load_real_tiff(image_path)
        item = info[stem]
        if not valid.all() or image.shape != (item['height'], item['width']):
            raise ValueError('Invalid pixels or annotation coordinate mismatch')
        h, w = image.shape
        if min(h, w) < 128:
            raise ValueError('Image too small for fixed native crop')
        y, x = (h - 128) // 2, (w - 128) // 2
        rim = rasterise_image_annotations(annotations, item['id'], h, w, mode='rim', rim_width=1)
        crop = image[y:y+128, x:x+128].copy()
        reference = rim[y:y+128, x:x+128].copy()
        folder = output / 'cases' / stem
        folder.mkdir(parents=True, exist_ok=True)
        Image.fromarray(crop).save(folder / 'input.png')
        Image.fromarray(reference).save(folder / 'reference.png')
        records.append({**case, 'image_info': item, 'crop_xywh': [x, y, 128, 128],
                        'source_image_sha256': digest(image_path),
                        'input_pixel_sha256': hashlib.sha256(crop.tobytes()).hexdigest(),
                        'reference_pixel_sha256': hashlib.sha256(reference.tobytes()).hexdigest(),
                        'reference_pixels_scored': int(np.count_nonzero(reference[2:-2, 2:-2])),
                        'loading': loading})
    manifest = {'protocol_sha256': digest(protocol_path), 'metadata_sha256': digest(metadata_path),
                'annotations_sha256': digest(annotation_path), 'cases': records}
    write_json(output / 'dataset.json', manifest)
    return manifest


def exact_magnitude(image, inequality=False):
    import numpy as np
    values = np.floor(image.astype(float) / 255 * 15) if inequality else image.astype(float)
    gx, gy = np.zeros(values.shape), np.zeros(values.shape)
    dx, dy = np.diff(values, axis=1), np.diff(values, axis=0)
    gx[:, 1:] = (dx != 0) if inequality else dx
    gy[1:, :] = (dy != 0) if inequality else dy
    return np.hypot(gx, gy)


def measure(scores, reference):
    import numpy as np
    from quantum.reconstruction import threshold_edge_map
    from evaluation.metrics import compute_all_metrics
    binary, threshold = threshold_edge_map(scores, 'otsu')
    # Threshold on full crop; exclude an identical 2px border for every method.
    region = np.s_[2:-2, 2:-2]
    metrics = compute_all_metrics(binary[region], scores[region], reference[region])
    metrics.pop('method')
    # Empty references remain in the sample. Avoid nonstandard JSON Infinity.
    metrics['chamfer'] = metrics['chamfer'] if math.isfinite(metrics['chamfer']) else None
    metrics.update(coverage=float(np.mean(binary[region] > 0)), threshold=threshold)
    return metrics, binary


def classical(output, case):
    import numpy as np
    from PIL import Image
    from classical.sobel import sobel_edge
    from classical.canny import canny_edge_auto
    from classical.robinson_compass import robinson_edge
    folder = output / 'cases' / case['stem']
    image = np.array(Image.open(folder / 'input.png'))
    reference = np.array(Image.open(folder / 'reference.png'))
    methods = {'Sobel': lambda: sobel_edge(image),
               'Canny': lambda: canny_edge_auto(image),
               'Robinson': lambda: robinson_edge(image)[0],
               'Exact-gradient': lambda: exact_magnitude(image),
               'Exact-NEQR-inequality': lambda: exact_magnitude(image, True)}
    records = []
    for method, detector in methods.items():
        started = time.perf_counter()
        scores = detector().astype(float)
        elapsed = time.perf_counter() - started
        if scores.max():
            scores /= scores.max()
        metrics, binary = measure(scores, reference)
        metrics.update(method=method, stem=case['stem'], seed=None, shots=0,
                       elapsed_seconds=elapsed, operator_rmse=0.0 if method.startswith('Exact-') else None)
        np.savez_compressed(folder / (method + '.npz'), strength=scores, binary=binary)
        records.append(metrics)
    return records


def worker(output, method, stem, shots, seed):
    """One isolated worker binds its repository's ENCODING before imports."""
    repo = NEQR_ROOT if method == 'NEQR' else ROOT
    sys.path.insert(0, str(repo))
    import numpy as np
    from PIL import Image
    from importlib.metadata import version
    from quantum.variant_circuit import ENCODING
    if method == 'QPIE':
        from quantum.qpie_full_image import run_full_image_qhed
    else:
        if ENCODING != method:
            raise ValueError('Worker imported wrong repository encoding')
        from quantum.full_image import run_full_image_qhed
    folder = output / 'cases' / stem
    image = np.array(Image.open(folder / 'input.png'))
    reference = np.array(Image.open(folder / 'reference.png'))
    run_folder = output / 'runs' / f'{stem}_{method}_s{shots}_seed{seed}'
    run_folder.mkdir(parents=True, exist_ok=True)
    maps, execution, _ = run_full_image_qhed(image, tile_size=16, shots=shots,
        seed=seed, batch_tiles=16, subtract_tile_min=False,
        audit_path=run_folder / 'counts.jsonl.gz')
    metrics, binary = measure(maps['strength'], reference)
    exact = exact_magnitude(image, inequality=(method == 'NEQR'))
    region = np.s_[2:-2, 2:-2]
    rmse = float(np.sqrt(np.mean((maps['magnitude'][region] - exact[region]) ** 2)))
    metrics.update(method=method, stem=stem, shots=shots, seed=seed,
                   elapsed_seconds=execution['elapsed_seconds'], operator_rmse=rmse,
                   circuits=execution['circuits_executed'], measurement_shots=execution['measurement_shots'])
    if execution['qubits_per_circuit'] != {'QPIE': 8, 'FRQI': 9, 'NEQR': 12}[method]:
        raise ValueError('Wrong encoding qubit count')
    np.savez_compressed(run_folder / 'maps.npz', **maps, binary=binary)
    write_json(run_folder / 'result.json', {
        'metrics': metrics, 'execution': execution,
        'input_pixel_sha256': hashlib.sha256(image.tobytes()).hexdigest(),
        'protocol_sha256': digest(output / 'protocol.json'),
        'versions': {key: version(key) for key in ('qiskit', 'qiskit-aer', 'numpy')},
    })


def aggregate(records):
    """Seeds are repeated measurements, not independent image samples."""
    import numpy as np
    groups = {}
    for record in records:
        groups.setdefault((record['method'], record['shots']), {}).setdefault(record['stem'], []).append(record)
    summaries, per_image = [], {}
    for (method, shots), images in sorted(groups.items()):
        means = {}
        for stem, runs in images.items():
            means[stem] = {metric: float(np.mean([r[metric] for r in runs if r.get(metric) is not None]))
                           if any(r.get(metric) is not None for r in runs) else None
                           for metric in METRICS}
        summary = {'method': method, 'shots': shots, 'images': len(images),
                   'runs': sum(map(len, images.values()))}
        for metric in METRICS:
            values = [r[metric] for r in means.values() if r[metric] is not None]
            summary[metric] = float(np.mean(values)) if values else None
        per_image[f'{method}:{shots}'] = means
        summaries.append(summary)
    return summaries, per_image


def paired_bootstrap(per_image, a, b, metric='pr_auc'):
    import numpy as np
    if set(per_image[a]) != set(per_image[b]):
        raise ValueError('Paired comparison requires identical images')
    stems = sorted(per_image[a])
    differences = np.array([per_image[a][s][metric] - per_image[b][s][metric] for s in stems])
    rng = np.random.default_rng(20261019)
    sampled = differences[rng.integers(0, len(stems), (10000, len(stems)))].mean(axis=1)
    low, high = np.quantile(sampled, [.025, .975])
    return {'a': a, 'b': b, 'metric': metric, 'mean_difference': float(differences.mean()),
            'ci95_low': float(low), 'ci95_high': float(high), 'image_pairs': len(stems)}


def report(output, records, manifest):
    summaries, per_image = aggregate(records)
    pairs = [paired_bootstrap(per_image, f'{a}:{shots}', f'{b}:{shots}')
             for shots in BUDGETS for a, b in (('QPIE', 'FRQI'), ('QPIE', 'NEQR'), ('FRQI', 'NEQR'))]
    pairs += [paired_bootstrap(per_image, f'{a}:{shots}', f'{b}:0')
              for shots in BUDGETS for a in METHODS
              for b in ('Robinson', 'Exact-gradient' if a != 'NEQR' else 'Exact-NEQR-inequality')]
    write_json(output / 'summary.json', {'summary': summaries, 'per_image': per_image, 'paired_ap': pairs})
    with (output / 'runs.csv').open('w', newline='', encoding='utf-8') as handle:
        fields = sorted(set().union(*(r.keys() for r in records)))
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    rows = ['# Matched quantum encoding benchmark', '',
            'Eight test-split products excluded from the prior 30-image selection (including their product IDs). '
            'One fixed native 128x128 center crop per image; no label-based selection or resizing. '
            'This is a crop-scale test-partition study, not a full-image or proven geographically independent benchmark.', '',
            'All methods receive identical mean-band, full-tile 2-98 percentile grayscale crops. '
            'All quantum runs disable block-minimum subtraction, use 16x16 blocks with 14x14 cores, '
            'four passes, seeds 42/43/44 and 1024/8192 shots per circuit. '
            'There is no smoothing, noise model, or trace capture. Outputs come from actual Aer measurements.', '',
            'Continuous maps use the same float Otsu implementation. Canny retains its automatic median thresholds. '
            'Metrics exclude a 2px crop border for every method. Catalog rims are 1px approximate circular references. '
            'No labels tune thresholds. Classical exact-gradient and exact-NEQR-inequality isolate the operators from shot noise.', '',
            '## Results', '', 'Seeds are averaged within image before the eight-image macro average. '
            'AP denotes average precision, not trapezoidal PR area. Canny has binary scores. '
            'RMSE is in grayscale intensity units for QPIE/FRQI and inequality-response units for NEQR; '
            'do not compare these RMSE units across operators.', '',
            '| Method | Shots/circuit | Exact F1 | 2px F1 | AP | Edge coverage | Operator RMSE | Detector seconds |',
            '|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in summaries:
        rmse = '-' if s['operator_rmse'] is None else f"{s['operator_rmse']:.4f}"
        rows.append(f"| {s['method']} | {s['shots']} | {s['f1_exact']:.4f} | {s['f1_2px']:.4f} | "
                    f"{s['pr_auc']:.4f} | {s['coverage']:.1%} | {rmse} | {s['elapsed_seconds']:.4f} |")
    rows += ['', '## Paired image bootstrap for AP', '',
             '10,000 paired resamples of eight image-level means, fixed bootstrap seed 20261019. '
             'Intervals are exploratory, unadjusted for multiple comparisons, and limited by the small image sample. '
             'Repeated simulator seeds are not treated as independent images.', '',
             '| A | B | AP difference A-B | 95% interval |', '|---|---|---:|---|']
    for p in pairs:
        rows.append(f"| {p['a']} | {p['b']} | {p['mean_difference']:.4f} | [{p['ci95_low']:.4f}, {p['ci95_high']:.4f}] |")
    circuits = sum(r.get('circuits', 0) for r in records)
    shots = sum(r.get('measurement_shots', 0) for r in records)
    rows += ['', '## Verification and limits', '',
             f'Completed {len(records)} metric records: 144 quantum runs and 40 deterministic classical/control runs. '
             f'Quantum totals: {circuits:,} circuits and {shots:,} shots.', '',
             'Each result stores execution totals, protocol hash, input pixel hash and runtime versions; '
             'maps and compressed counts are retained for independent recomputation. Counts are checked '
             'against requested shots for every circuit, including an independent audit-file verification. '
             'Detector timings include count-audit writes and exclude imports, input image I/O, preprocessing, metrics and map serialization. '
             'Timings are descriptive ideal-simulator measurements, not evidence of quantum hardware speedup.', '',
             'NEQR uses four intensity bits and detects inequality, not intensity-gradient magnitude. '
             'QPIE and FRQI have the same exact calibrated gradient target but different sampling distributions. '
             'Eight center crops cannot establish full-tile crater detection performance, and catalog rims are approximate. '
             'Excluding product IDs does not prove geographic independence from all historic development data.', '',
             '## Data and reproducibility', '',
             f'Dataset: NASA-IBM AI4Science SomBench WAC Crater Detection, revision `{REVISION}`. '
             'Attribution: NASA-IBM AI4Science SomBench; Robbins (2019) crater catalog. License: CC BY 4.0.', '',
             'Run: `.venv/Scripts/python.exe experiments/benchmark_encodings.py`. '
             'Resume requires identical protocol and source hashes. '
             'Inspect `protocol.json`, `dataset.json`, `runs.csv`, `summary.json` and `verification.json`.', '',
             '## Selected cases', '', '| Product / tile | Positive reference pixels scored |', '|---|---:|']
    rows += [f"| {c['stem']} | {c['reference_pixels_scored']} |" for c in manifest['cases']]
    (output / 'report.md').write_text('\n'.join(rows) + '\n', encoding='utf-8')


def verify(output, records, manifest):
    import numpy as np
    from PIL import Image
    cases = {c['stem']: c for c in manifest['cases']}
    checks = 0
    for record in records:
        stem, method, shots, seed = (record[k] for k in ('stem', 'method', 'shots', 'seed'))
        folder = output / 'cases' / stem
        reference = np.array(Image.open(folder / 'reference.png'))
        if method in METHODS:
            run = output / 'runs' / f'{stem}_{method}_s{shots}_seed{seed}'
            info = json.loads((run / 'result.json').read_text())
            if info['protocol_sha256'] != digest(output / 'protocol.json'):
                raise ValueError('Protocol mismatch')
            if info['input_pixel_sha256'] != cases[stem]['input_pixel_sha256']:
                raise ValueError('Input mismatch')
            if record['circuits'] != 400 or record['measurement_shots'] != 400 * shots:
                raise ValueError('Circuit/shot total mismatch')
            if info['execution']['subtract_tile_min']:
                raise ValueError('Unmatched preparation')
            with gzip.open(run / 'counts.jsonl.gz', 'rt', encoding='utf-8') as handle:
                audit = [json.loads(line) for line in handle]
            keys = {(a['tile_y'], a['tile_x'], a['direction'], a['pair_offset']) for a in audit}
            expected_keys = {(y, x, direction, offset)
                             for y in range(0, 128, 14) for x in range(0, 128, 14)
                             for direction in ('horizontal', 'vertical') for offset in (0, 1)}
            if len(audit) != 400 or keys != expected_keys:
                raise ValueError('Missing/duplicate audit circuits')
            if any(sum(a['counts'].values()) != shots or a['shots'] != shots
                   or a['preparation_offset'] != 0 for a in audit):
                raise ValueError('Count audit or preparation mismatch')
            maps = np.load(run / 'maps.npz')
            target = exact_magnitude(np.array(Image.open(folder / 'input.png')), method == 'NEQR')
            rmse = float(np.sqrt(np.mean((maps['magnitude'][2:-2, 2:-2] - target[2:-2, 2:-2]) ** 2)))
            if not np.isclose(rmse, record['operator_rmse'], atol=1e-12):
                raise ValueError('Operator RMSE mismatch')
        else:
            maps = np.load(folder / (method + '.npz'))
        actual, binary = measure(maps['strength'], reference)
        for metric in ('f1_exact', 'f1_1px', 'f1_2px', 'pr_auc', 'iou', 'coverage'):
            if not np.isclose(actual[metric], record[metric], atol=1e-12):
                raise ValueError('Metric recomputation mismatch: ' + metric)
        np.testing.assert_array_equal(binary, maps['binary'])
        if not np.isfinite(maps['strength']).all():
            raise ValueError('Nonfinite map')
        checks += 1
    expected = {(case['stem'], method, shots, seed) for case in manifest['cases']
                for method in METHODS for shots in BUDGETS for seed in SEEDS}
    observed = {(r['stem'], r['method'], r['shots'], r['seed']) for r in records if r['method'] in METHODS}
    if expected != observed or len(records) != 184:
        raise ValueError('Incomplete/duplicate benchmark matrix')
    write_json(output / 'verification.json', {'status': 'passed', 'records_recomputed': checks,
        'quantum_runs': len(observed), 'unique_test_images': len(cases),
        'total_circuits': sum(r.get('circuits', 0) for r in records),
        'total_shots': sum(r.get('measurement_shots', 0) for r in records),
        'checks': ['complete matrix', 'input/protocol hashes', 'matched preparation',
                   'execution totals', '400 unique audited circuits/run and exact shot sums',
                   'saved metric and threshold recomputation', 'operator RMSE recomputation',
                   'binary map equality', 'finite strength maps']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--worker', choices=METHODS)
    parser.add_argument('--stem')
    parser.add_argument('--shots', type=int)
    parser.add_argument('--seed', type=int)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    if args.worker:
        worker(output, args.worker, args.stem, args.shots, args.seed)
        return
    sys.path.insert(0, str(ROOT))
    output.mkdir(parents=True, exist_ok=True)
    manifest = prepare(output)
    if args.prepare_only:
        return
    records = []
    # Fixed randomized order reduces systematic method/shot timing drift.
    import numpy as np
    tasks = [(case['stem'], method, shots, seed) for case in manifest['cases']
             for method in METHODS for shots in BUDGETS for seed in SEEDS]
    np.random.default_rng(20261019).shuffle(tasks)
    for case in manifest['cases']:
        records.extend(classical(output, case))
    for number, (stem, method, shots, seed) in enumerate(tasks, 1):
        result_path = output / 'runs' / f'{stem}_{method}_s{shots}_seed{seed}' / 'result.json'
        if not result_path.exists():
            command = [sys.executable, '-u', str(Path(__file__).resolve()), '--output', str(output),
                       '--worker', method, '--stem', stem, '--shots', str(shots), '--seed', str(seed)]
            options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
            subprocess.run(command, check=True, timeout=600, **options)
        result = json.loads(result_path.read_text())
        if result['protocol_sha256'] != digest(output / 'protocol.json'):
            raise ValueError('Stale result, protocol differs')
        records.append(result['metrics'])
        print(f"{number}/144 {method} shots={shots} seed={seed} {stem}: "
              f"AP={result['metrics']['pr_auc']:.4f} time={result['metrics']['elapsed_seconds']:.2f}s", flush=True)
    verify(output, records, manifest)
    report(output, records, manifest)
    print('Completed and verified: ' + str(output / 'report.md'), flush=True)


if __name__ == '__main__':
    main()
