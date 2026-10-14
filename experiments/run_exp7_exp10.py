"""
Experiment 7 -- Preprocessing Strategy Comparison
Experiment 10 -- Failure Taxonomy

These run after the main experiments complete.
"""
import numpy as np
import csv
import sys
import time
from pathlib import Path
from PIL import Image
import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from classical.sobel import sobel_edge, sobel_edge_binary
from classical.robinson_compass import robinson_edge_binary
from evaluation.metrics import compute_all_metrics, boundary_f1
from quantum.qhed_circuit import run_qhed_combined
from quantum.quantum_gradient import quantum_gradient_from_neqr
from preprocessing.preprocessor import preprocess

RESULTS_DIR = PROJECT_ROOT / "results" / "corrected" / "tables"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
N_TRIALS = 10
DEFAULT_SHOTS = 8192


def load_synthetic_patches(size=8):
    img_dir = PROJECT_ROOT / "data" / "synthetic" / "images"
    mask_dir = PROJECT_ROOT / "data" / "synthetic" / "masks"
    patches = []
    for img_path in sorted(img_dir.glob(f"*_{size}x{size}.png")):
        name = img_path.stem.replace(f"_{size}x{size}", "")
        mask_path = mask_dir / f"{name}_{size}x{size}_mask.png"
        if mask_path.exists():
            img = np.array(Image.open(img_path))
            mask = np.array(Image.open(mask_path))
            if np.sum(mask > 0) > 0:
                patches.append({'name': name, 'image': img, 'mask': mask, 'size': size})
    return patches


def run_quantum_qhed(image, shots=DEFAULT_SHOTS, seed_simulator=42):
    combined, _, _ = run_qhed_combined(image.astype(np.float64), shots=shots, seed_simulator=seed_simulator)
    nonzero = combined[combined > 0]
    thresh = np.median(nonzero) if len(nonzero) > 0 else 0.5
    binary = (combined >= thresh).astype(np.uint8) * 255
    continuous = combined
    return binary, continuous


def run_quantum_neqr(image, shots=DEFAULT_SHOTS, seed_simulator=42):
    edge_map, recon, qc = quantum_gradient_from_neqr(image, intensity_bits=4, shots=shots, seed_simulator=seed_simulator)
    nonzero = edge_map[edge_map > 0]
    thresh = np.median(nonzero) if len(nonzero) > 0 else 0.5
    binary = (edge_map >= thresh).astype(np.uint8) * 255
    continuous = edge_map
    return binary, continuous


def experiment_7():
    """Experiment 7 -- Preprocessing strategy comparison."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 7: Preprocessing Strategy Comparison")
    print("=" * 60)

    patches = load_synthetic_patches(8)[:3]
    preprocess_configs = [
        ("none", {}),
        ("gaussian", {"sigma": 1.0}),
        ("median", {"ksize": 3}),
        ("clahe", {"clip_limit": 2.0, "tile_size": (4, 4)}),
        ("histogram_stretch", {}),
        ("gamma", {"gamma": 0.5}),
        ("gamma", {"gamma": 1.5}),
    ]
    preprocess_names = [
        "none", "gaussian_s1", "median_3x3", "clahe",
        "hist_stretch", "gamma_0.5", "gamma_1.5"
    ]
    methods = ["Sobel", "Robinson", "QPIE-QHED", "NEQR-Gradient"]
    results = []

    for p in patches:
        print(f"\n  Image: {p['name']}")
        for (pp_method, pp_kwargs), pp_name in zip(preprocess_configs, preprocess_names):
            processed = preprocess(p['image'], pp_method, **pp_kwargs)
            
            for method in methods:
                f1_values = []
                for trial in range(N_TRIALS if "Q" in method or "NEQR" in method else 1):
                    if method == "Sobel":
                        binary, _ = sobel_edge_binary(processed)
                        continuous = sobel_edge(processed)
                    elif method == "Robinson":
                        binary, continuous, _ = robinson_edge_binary(processed)
                    elif method == "QPIE-QHED":
                        binary, continuous = run_quantum_qhed(processed, seed_simulator=42 + trial)
                    elif method == "NEQR-Gradient":
                        binary, continuous = run_quantum_neqr(processed, seed_simulator=42 + trial)
                    
                    m = compute_all_metrics(binary, continuous, p['mask'], method)
                    f1_values.append(m['f1_exact'])
                
                results.append({
                    'image': p['name'],
                    'preprocessing': pp_name,
                    'method': method,
                    'f1_exact_mean': np.mean(f1_values),
                    'f1_exact_std': np.std(f1_values),
                })
            
            best = max(results[-4:], key=lambda r: r['f1_exact_mean'])
            print(f"    {pp_name:<15} best={best['method']:<15} F1={best['f1_exact_mean']:.4f}")

    # Save
    path = RESULTS_DIR / "exp7_preprocessing.csv"
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        for r in results:
            row = {k: f"{v:.4f}" if isinstance(v, float) else v for k, v in r.items()}
            writer.writerow(row)
    print(f"  Saved: {path}")
    return results


def experiment_10():
    """Experiment 10 -- Failure Taxonomy.
    
    Classifies failure modes of quantum methods:
    - Complete miss (F1=0): quantum sees no edges
    - Over-detection: quantum marks non-edge pixels
    - Under-detection: quantum misses real edges
    - Displacement: edges detected but shifted
    - Direction-specific: fails on certain orientations
    """
    print("\n" + "=" * 60)
    print("EXPERIMENT 10: Failure Taxonomy")
    print("=" * 60)

    patches = load_synthetic_patches(8)
    results = []

    for p in patches:
        for method_name, run_fn in [("QPIE-QHED", run_quantum_qhed), 
                                     ("NEQR-Gradient", run_quantum_neqr)]:
            # Run multiple trials
            f1_exact_list = []
            f1_1px_list = []
            precision_list = []
            recall_list = []
            predicted_pixels = []
            
            for trial in range(N_TRIALS):
                binary, continuous = run_fn(p['image'], seed_simulator=42 + trial)
                predicted_pixels.append(np.count_nonzero(binary))
                m = compute_all_metrics(binary, continuous, p['mask'], method_name)
                f1_exact_list.append(m['f1_exact'])
                f1_1px_list.append(m['f1_1px'])
                precision_list.append(m['precision_exact'])
                recall_list.append(m['recall_exact'])
            
            mean_f1 = np.mean(f1_exact_list)
            mean_f1_1px = np.mean(f1_1px_list)
            mean_p = np.mean(precision_list)
            mean_r = np.mean(recall_list)
            
            # Classify failure mode
            if np.mean(predicted_pixels) == 0:
                failure_mode = "COMPLETE_MISS"
            elif mean_f1 == 0 and mean_p == 0:
                failure_mode = "OVER_DETECTION"
            elif mean_f1 < 0.1 and mean_r < 0.1:
                failure_mode = "UNDER_DETECTION"
            elif mean_f1 < 0.3 and mean_f1_1px > mean_f1 * 2:
                failure_mode = "DISPLACEMENT"
            elif mean_f1 < 0.3:
                failure_mode = "LOW_QUALITY"
            elif mean_f1 < 0.5:
                failure_mode = "MODERATE"
            else:
                failure_mode = "SUCCESS"
            
            results.append({
                'geometry': p['name'],
                'method': method_name,
                'f1_exact_mean': mean_f1,
                'f1_exact_std': np.std(f1_exact_list),
                'f1_1px_mean': mean_f1_1px,
                'precision_mean': mean_p,
                'recall_mean': mean_r,
                'failure_mode': failure_mode,
            })
            
            print(f"  {p['name']:<20} {method_name:<15} "
                  f"F1={mean_f1:.4f} P={mean_p:.4f} R={mean_r:.4f} "
                  f"-> {failure_mode}")

    # Save
    path = RESULTS_DIR / "exp10_failure_taxonomy.csv"
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        for r in results:
            row = {k: f"{v:.4f}" if isinstance(v, float) else v for k, v in r.items()}
            writer.writerow(row)
    print(f"  Saved: {path}")

    # Summary
    print("\n  Failure Mode Summary:")
    from collections import Counter
    for method in ["QPIE-QHED", "NEQR-Gradient"]:
        mr = [r for r in results if r['method'] == method]
        modes = Counter(r['failure_mode'] for r in mr)
        print(f"    {method}: {dict(modes)}")

    return results


def main():
    np.random.seed(42)
    total_start = time.time()

    experiment_7()
    experiment_10()

    total_time = time.time() - total_start
    print(f"\nTotal time: {total_time / 60:.1f} minutes")


if __name__ == "__main__":
    main()
