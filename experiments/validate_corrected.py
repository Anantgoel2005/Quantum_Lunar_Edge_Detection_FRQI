"""Seeded validation benchmark; preserves the original published result tables."""
import argparse
import csv
import json
import sys
from importlib.metadata import version
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.run_all_experiments import evaluate_method, run_quantum_qhed, run_quantum_neqr
from classical.finite_difference import forward_gradient, quantized_gradient
from classical.classical_pipeline import run_classical_pipeline
from classical.canny import canny_edge_auto

METHODS = ['Sobel', 'Canny', 'Robinson', 'Forward-Gradient', 'Quantized-Gradient', 'QPIE-QHED', 'NEQR-Gradient']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials', type=int, default=3)
    parser.add_argument('--shots', type=int, default=8192)
    args = parser.parse_args()
    if args.trials < 1 or args.shots < 1:
        parser.error('trials and shots must be positive')
    output = ROOT / 'results' / 'corrected' / 'tables'
    output.mkdir(parents=True, exist_ok=True)
    rows, negatives = [], []
    for dataset, images, masks in [('synthetic', ROOT/'data/synthetic/images', ROOT/'data/synthetic/masks'),
                                   ('lunar', ROOT/'data/sombench/patches', ROOT/'data/sombench/masks')]:
        for image_path in sorted(images.glob('*.png')):
            if dataset == 'synthetic' and not image_path.stem.endswith('_8x8'):
                continue
            mask_path = masks / (image_path.stem + '_mask.png')
            image, mask = np.array(Image.open(image_path)), np.array(Image.open(mask_path))
            print(f'{dataset}: {image_path.stem}', flush=True)
            for method in METHODS:
                n = args.trials if method in ['QPIE-QHED', 'NEQR-Gradient'] else 1
                if np.any(mask):
                    results = [evaluate_method(image, mask, method, args.shots, seed_simulator=42+t) for t in range(n)]
                    row = {'dataset': dataset, 'image': image_path.stem, 'size': image.shape[0], 'method': method,
                           'trials': n, 'shots_per_circuit': args.shots if n == args.trials and method in ['QPIE-QHED','NEQR-Gradient'] else 0,
                           'circuits_per_trial': 4 if method == 'QPIE-QHED' else (1 if method == 'NEQR-Gradient' else 0)}
                    for metric in ['f1_exact', 'pr_auc']:
                        vals = [result[metric] for result in results]
                        row[metric+'_mean'], row[metric+'_std'] = float(np.mean(vals)), float(np.std(vals))
                    rows.append(row)
                else:
                    # Evaluate negatives explicitly as false positive counts.
                    classic = run_classical_pipeline(image)
                    totals = []
                    for t in range(n):
                        if method == 'QPIE-QHED':
                            binary = run_quantum_qhed(image, args.shots, seed_simulator=42+t)[0]
                        elif method == 'NEQR-Gradient':
                            binary = run_quantum_neqr(image, args.shots, seed_simulator=42+t)[0]
                        elif method in ['Forward-Gradient','Quantized-Gradient']:
                            scores = forward_gradient(image) if method == 'Forward-Gradient' else quantized_gradient(image)
                            positive = scores[scores > 0]
                            binary = scores >= (np.median(positive) if len(positive) else 0.5)
                        elif method == 'Canny':
                            binary = canny_edge_auto(image)
                        else:
                            binary = classic['sobel_binary' if method == 'Sobel' else 'robinson_binary']
                        totals.append(int(np.count_nonzero(binary)))
                    negatives.append({'dataset': dataset, 'image': image_path.stem, 'size': image.shape[0],
                        'method': method, 'false_positive_pixels_mean': float(np.mean(totals)), 'pixels': image.size})
    for name, records in [('validation_benchmark.csv', rows), ('negative_patch_check.csv', negatives)]:
        if records:
            with (output/name).open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(records[0]))
                writer.writeheader()
                writer.writerows(records)
    metadata = {'trials': args.trials, 'shots_per_circuit': args.shots, 'seed_start': 42,
        'pr_auc_definition': 'average_precision',
        'qhed_circuits_per_trial': 4, 'positive_entries': len(rows), 'negative_entries': len(negatives),
        'versions': {name: version(name) for name in ['qiskit','qiskit-aer','numpy','scipy','opencv-python','Pillow','scikit-learn']}}
    (output.parent/'validation_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
