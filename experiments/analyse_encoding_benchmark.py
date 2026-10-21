"""Supplement the frozen benchmark with metadata-only overlap sensitivity checks."""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments import benchmark_encodings as benchmark


def geographic_overlaps(cases, metadata, prior_stems):
    """Conservative projected bounding-box overlap within the same LTM zone."""
    previous = [r for r in metadata if Path(r['WAC_VIS_TILE']).stem in prior_stems]
    overlaps = []
    for case in cases:
        m = case['metadata']
        x, y, w, h = case['crop_xywh']
        dx = (m['BOUNDS_XMAX'] - m['BOUNDS_XMIN']) / case['image_info']['width']
        dy = (m['BOUNDS_YMAX'] - m['BOUNDS_YMIN']) / case['image_info']['height']
        left, right = m['BOUNDS_XMIN'] + x * dx, m['BOUNDS_XMIN'] + (x+w) * dx
        top, bottom = m['BOUNDS_YMAX'] - y * dy, m['BOUNDS_YMAX'] - (y+h) * dy
        for row in previous:
            if row['LTM_CODE'] == m['LTM_CODE'] and (
                max(left, row['BOUNDS_XMIN']) < min(right, row['BOUNDS_XMAX']) and
                max(bottom, row['BOUNDS_YMIN']) < min(top, row['BOUNDS_YMAX'])
            ):
                overlaps.append({'benchmark': case['stem'], 'prior': Path(row['WAC_VIS_TILE']).stem})
    return overlaps


def main():
    import pyarrow.parquet as pq
    import numpy as np
    from PIL import Image
    output = benchmark.DEFAULT_OUTPUT
    protocol = json.loads((output / 'protocol.json').read_text())
    dataset = json.loads((output / 'dataset.json').read_text())
    metadata = pq.read_table(ROOT / 'data/sombench/cache' / benchmark.REVISION / 'metadata.parquet').to_pylist()
    overlaps = geographic_overlaps(dataset['cases'], metadata, set(protocol['excluded_stems']))
    excluded = {pair['benchmark'] for pair in overlaps}
    # Read typed records from the actual run files, avoiding CSV type inference.
    records = []
    for path in (output / 'runs').glob('*/result.json'):
        record = json.loads(path.read_text())['metrics']
        reference = np.array(Image.open(output / 'cases' / record['stem'] / 'reference.png'))
        with np.load(path.parent / 'maps.npz') as maps:
            actual, _ = benchmark.measure(maps['strength'], reference)
        if not np.isclose(actual['threshold'], record['threshold'], atol=1e-12):
            raise ValueError('Stored Otsu threshold mismatch')
        records.append(record)
    for case in dataset['cases']:
        records.extend(benchmark.classical(output, case))
    subset = [r for r in records if r['stem'] not in excluded]
    summaries, per_image = benchmark.aggregate(subset)
    _, all_images = benchmark.aggregate(records)
    pairs = [benchmark.paired_bootstrap(per_image, f'{a}:{shots}', f'{b}:{shots}')
             for shots in benchmark.BUDGETS
             for a, b in (('QPIE', 'FRQI'), ('QPIE', 'NEQR'), ('FRQI', 'NEQR'))]
    pairs += [benchmark.paired_bootstrap(per_image, f'{a}:{shots}', 'Robinson:0')
              for shots in benchmark.BUDGETS for a in benchmark.METHODS]
    shot_effects = [benchmark.paired_bootstrap(all_images, f'{method}:8192', f'{method}:1024')
                    for method in benchmark.METHODS]
    timing = []
    for method in benchmark.METHODS:
        for shots in benchmark.BUDGETS:
            runs = [r for r in records if r['method'] == method and r['shots'] == shots]
            seconds = np.array([r['elapsed_seconds'] for r in runs])
            median = float(np.median(seconds))
            timing.append({'method': method, 'shots': shots, 'median_seconds': median,
                           'p25_seconds': float(np.quantile(seconds, .25)),
                           'p75_seconds': float(np.quantile(seconds, .75)),
                           'maximum_seconds': float(seconds.max()),
                           'flagged_above_5x_group_median': [
                               {'stem': r['stem'], 'seed': r['seed'], 'seconds': r['elapsed_seconds']}
                               for r in runs if r['elapsed_seconds'] > 5 * median]})
    analysis = {
        'criterion': 'Positive-area projected bounding-box overlap: selected center crop vs any full prior selected30 tile in same LTM_CODE',
        'overlaps': overlaps, 'excluded_from_sensitivity': sorted(excluded),
        'sensitivity_images': len(dataset['cases']) - len(excluded),
        'summary': summaries, 'paired_ap': pairs, 'all8_shot_effects_ap': shot_effects,
        'limits': 'This excludes known selected30 bounding-box overlap only, not all training images or prior research. Exploratory metadata-only sensitivity, specified during execution after initial runs; frozen primary results retained.',
        'analysis_script_sha256': benchmark.digest(__file__),
        'quantum_thresholds_recomputed': len(records) - len(dataset['cases']) * 5,
        'timing_distributions': timing,
    }
    benchmark.write_json(output / 'geographic_sensitivity.json', analysis)
    replay = json.loads((output / 'count_replay_verification.json').read_text())
    rows = ['', '## Additional audit and interpretation', '',
            'Boundary-tolerant F1 uses square binary dilation (Chebyshev pixel tolerance), '
            'as implemented by the existing evaluation module. Label-location uncertainty is not '
            'included in the bootstrap intervals.', '',
            'Finite-shot interpretation: for a 16x16 FRQI block, a single accepted count corresponds '
            'to a calibrated difference of '
            f"{1020/np.pi*np.arcsin(np.sqrt(256/(2*1024))):.1f} grayscale units at 1024 shots or "
            f"{1020/np.pi*np.arcsin(np.sqrt(256/(2*8192))):.1f} units at 8192 shots. "
            'Smaller true differences can still generate a count, but often produce zero observed counts. '
            'This is a sampling limitation, not a hard input quantization cutoff. '
            'NEQR instead tests inequality between four-bit levels, so its operator and RMSE units differ.', '',
            f"Independent replay decoded all {replay['circuits_replayed']:,} count dictionaries "
            f"({replay['measurement_shots_replayed']:,} shots) without importing detector/reconstruction code. "
            f"Maximum magnitude discrepancy: {replay['maximum_absolute_magnitude_error']:.3g}. "
            'See `count_replay_verification.json` and `experiments/verify_encoding_counts.py`.', '',
            '### Known geographic overlap sensitivity', '',
            f"Metadata bounding-box checks found {len(excluded)} center crops overlapping full tiles in the previous "
            '30-image selection despite having different product IDs. The frozen eight-image primary analysis remains above. '
            'The following exploratory subset excludes these overlaps without selecting replacement cases. '
            'The rule uses metadata only and was specified during execution, after initial runs. '
            'This checks known prior-selection overlap, not independence from all training data or prior research.', '',
            '| Benchmark crop excluded from sensitivity | Prior tile with overlapping bounds |', '|---|---|']
    rows += [f"| {p['benchmark']} | {p['prior']} |" for p in overlaps]
    rows += ['', f"### Results on {analysis['sensitivity_images']} crops without known prior-selection bounds overlap", '',
             '| Method | Shots/circuit | Exact F1 | 2px F1 | AP |', '|---|---:|---:|---:|---:|']
    rows += [f"| {s['method']} | {s['shots']} | {s['f1_exact']:.4f} | {s['f1_2px']:.4f} | {s['pr_auc']:.4f} |"
             for s in summaries]
    rows += ['', '### Paired AP intervals on the geographic sensitivity subset', '',
             'Paired image bootstrap, 10,000 resamples, unadjusted exploratory 95% intervals.', '',
             '| A | B | AP difference A-B | 95% interval |', '|---|---|---:|---|']
    rows += [f"| {p['a']} | {p['b']} | {p['mean_difference']:.4f} | [{p['ci95_low']:.4f}, {p['ci95_high']:.4f}] |"
             for p in pairs]
    rows += ['', '### Effect of increasing shots on all eight crops', '',
             '| Method | AP difference 8192-1024 | Paired 95% interval |', '|---|---:|---|']
    rows += [f"| {p['a'].split(':')[0]} | {p['mean_difference']:.4f} | [{p['ci95_low']:.4f}, {p['ci95_high']:.4f}] |"
             for p in shot_effects]
    rows += ['', '### Timing diagnostics', '',
             'All timings are retained. The mean detector times in the primary table are sensitive to host '
             'scheduling or pauses. The distributions below are descriptive, not a controlled speed benchmark. '
             'Runs flagged above five times their group median are listed in `geographic_sensitivity.json`. '
             'Their circuits, shot totals and independent count replay are covered by the same verification '
             'as all other runs. Causes of elapsed-time outliers cannot be established from retained logs. '
             'No runs are excluded from numerical results based on runtime.', '',
             '| Method | Shots | Median seconds | 25th-75th percentile | Maximum seconds |',
             '|---|---:|---:|---|---:|']
    rows += [f"| {t['method']} | {t['shots']} | {t['median_seconds']:.3f} | "
             f"[{t['p25_seconds']:.3f}, {t['p75_seconds']:.3f}] | {t['maximum_seconds']:.3f} |"
             for t in timing]
    rows += ['', '### Figures and execution', '', '![Average precision](average_precision.png)', '',
             '![Selected inputs and catalog rims](inputs.png)', '',
             'The matrix was resumed with `experiments/run_encoding_matrix.py`, using one persistent isolated '
             'worker per encoding and executing tasks serially in the same fixed randomized order. '
             'Previously completed runs were retained only when their protocol hashes matched. '
             'Cold/warm in-call behavior can affect descriptive timings; no hardware-speed comparison is claimed. '
             'Execution driver identity and hash are in `execution_driver.json`.', '',
             'Reproduce the final bundle: run `experiments/run_encoding_matrix.py`, then '
             '`experiments/verify_encoding_counts.py`, `experiments/plot_encoding_benchmark.py`, and '
             '`experiments/analyse_encoding_benchmark.py`.', '',
             '### Review evidence for this execution', '',
             'See [quality review](quality_review.md) for Jev checkpoint outcomes and investigations, '
             '[independent summary verification](independent_summary_verification.json) for the separate '
             'CSV/provenance checks, and [count replay verification](count_replay_verification.json) '
             'for the independent measurement reconstruction.', '']
    path = output / 'report.md'
    primary = path.read_text(encoding='utf-8').split('\n## Additional audit and interpretation')[0]
    primary = re.sub(r'\n<!-- findings:start -->.*?<!-- findings:end -->\n', '\n', primary, flags=re.S)
    primary_summary = json.loads((output / 'summary.json').read_text())['summary']
    primary_quantum = max((s for s in primary_summary if s['method'] in benchmark.METHODS and s['shots'] == 8192), key=lambda s: s['pr_auc'])
    subset_quantum = max((s for s in summaries if s['method'] in benchmark.METHODS and s['shots'] == 8192), key=lambda s: s['pr_auc'])
    primary_classical = max((s for s in primary_summary if s['method'] in ('Sobel', 'Canny', 'Robinson')), key=lambda s: s['pr_auc'])
    subset_classical = max((s for s in summaries if s['method'] in ('Sobel', 'Canny', 'Robinson')), key=lambda s: s['pr_auc'])
    findings = ('## Findings\n\n'
                f"At 8192 shots, {primary_quantum['method']} has the highest quantum mean AP in the frozen "
                f"eight-case analysis ({primary_quantum['pr_auc']:.4f}), below {primary_classical['method']} "
                f"({primary_classical['pr_auc']:.4f}). In the {analysis['sensitivity_images']}-case subset without "
                f"detected prior-selection bounds overlap, {subset_quantum['method']} has the highest quantum "
                f"mean AP ({subset_quantum['pr_auc']:.4f}), below {subset_classical['method']} "
                f"({subset_classical['pr_auc']:.4f}). Quantum mean rankings therefore depend on the sample; "
                'these small, exploratory comparisons do not establish a universal encoding winner.\n\n'
                'Increasing the shot budget improves the sampled operators, but no quantum pipeline surpasses '
                'the strongest classical comparator in mean AP in either analysis. The scope is native crops '
                'and approximate crater rims, not full-image crater detection or quantum hardware advantage.\n')
    title, rest = primary.split('\n', 1)
    path.write_text(title + '\n\n<!-- findings:start -->\n' + findings + '<!-- findings:end -->\n' + rest + '\n'.join(rows), encoding='utf-8')
    print(json.dumps({'sensitivity_images': analysis['sensitivity_images'], 'overlaps': overlaps,
                      'all8_shot_effects_ap': shot_effects}, indent=2))


if __name__ == '__main__':
    main()
