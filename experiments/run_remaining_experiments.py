"""
Run remaining experiments (5, 8, 3, 4) and generate analysis.
Experiments 1, 2, 6, 9 are already complete.
"""
import numpy as np
import csv
import sys
import time
from pathlib import Path
from PIL import Image
import cv2

PROJECT_ROOT = Path(r"E:\projects\Quantum_Image")
sys.path.insert(0, str(PROJECT_ROOT))

from classical.sobel import sobel_edge, sobel_edge_binary
from classical.canny import canny_edge_auto
from classical.robinson_compass import robinson_edge_binary
from evaluation.metrics import compute_all_metrics
from quantum.qhed_circuit import run_qhed_combined
from quantum.quantum_gradient import quantum_gradient_from_neqr
from quantum.noise_models import get_experiment_noise_configs
from preprocessing.augmentor import (add_gaussian_noise, add_gaussian_blur,
                                     scale_contrast, add_illumination_gradient)

RESULTS_DIR = PROJECT_ROOT / "results" / "tables"
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


def load_sombench_patches(size=8):
    patches_dir = PROJECT_ROOT / "data" / "sombench" / "patches"
    masks_dir = PROJECT_ROOT / "data" / "sombench" / "masks"
    patches = []
    for img_path in sorted(patches_dir.glob(f"*_{size}x{size}.png")):
        name = img_path.stem
        mask_path = masks_dir / f"{name}_mask.png"
        if mask_path.exists():
            img = np.array(Image.open(img_path))
            mask = np.array(Image.open(mask_path))
            if np.sum(mask > 0) > 0:
                patches.append({'name': name, 'image': img, 'mask': mask, 'size': size})
    return patches


def run_quantum_qhed(image, shots, noise_model=None):
    combined, h_map, v_map = run_qhed_combined(
        image.astype(np.float64), shots=shots, noise_model=noise_model
    )
    nonzero = combined[combined > 0]
    thresh = np.median(nonzero) if len(nonzero) > 0 else 0.5
    binary = (combined >= thresh).astype(np.uint8) * 255
    continuous = (combined * 255).astype(np.uint8)
    return binary, continuous


def run_quantum_neqr(image, shots, noise_model=None):
    edge_map, recon, qc = quantum_gradient_from_neqr(
        image, intensity_bits=4, shots=shots, noise_model=noise_model
    )
    nonzero = edge_map[edge_map > 0]
    thresh = np.median(nonzero) if len(nonzero) > 0 else 0.5
    binary = (edge_map >= thresh).astype(np.uint8) * 255
    continuous = (edge_map * 255).astype(np.uint8)
    return binary, continuous


def evaluate_method(image, mask, method, shots=DEFAULT_SHOTS, noise_model=None):
    if method == "Sobel":
        binary, _ = sobel_edge_binary(image)
        continuous = sobel_edge(image)
    elif method == "Canny":
        binary = canny_edge_auto(image)
        continuous = binary
    elif method == "Robinson":
        binary, continuous, _ = robinson_edge_binary(image)
    elif method == "QPIE-QHED":
        binary, continuous = run_quantum_qhed(image, shots, noise_model)
    elif method == "NEQR-Gradient":
        binary, continuous = run_quantum_neqr(image, shots, noise_model)
    else:
        raise ValueError(f"Unknown method: {method}")
    return compute_all_metrics(binary, continuous, mask, method)


def run_trials(image, mask, method, n_trials=N_TRIALS, shots=DEFAULT_SHOTS, noise_model=None):
    results = []
    for _ in range(n_trials):
        m = evaluate_method(image, mask, method, shots, noise_model)
        results.append(m)
    keys = ['f1_exact', 'f1_1px', 'f1_2px', 'precision_exact', 'recall_exact', 'iou', 'chamfer', 'pr_auc']
    agg = {'method': method}
    for k in keys:
        vals = [r[k] for r in results]
        agg[f'{k}_mean'] = np.mean(vals)
        agg[f'{k}_std'] = np.std(vals)
    return agg


def save_results(results, filename):
    if not results:
        return
    path = RESULTS_DIR / filename
    fields = list(results[0].keys())
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for r in results:
            row = {}
            for k, v in r.items():
                row[k] = f"{v:.4f}" if isinstance(v, float) else v
            writer.writerow(row)
    print(f"  Saved: {path}")


# ============================================================

def experiment_4():
    """Experiment 4 -- Image Quality Degradation"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 4: Image Quality Degradation")
    print("=" * 60)

    patches = load_synthetic_patches(8)[:3]  # circle, corner, diagonal
    methods = ["Sobel", "Robinson", "QPIE-QHED", "NEQR-Gradient"]
    results = []

    degradations = [
        ("clean", lambda img: img.copy()),
        ("noise_10", lambda img: add_gaussian_noise(img, 10)),
        ("noise_30", lambda img: add_gaussian_noise(img, 30)),
        ("noise_50", lambda img: add_gaussian_noise(img, 50)),
        ("blur_0.5", lambda img: add_gaussian_blur(img, 0.5)),
        ("blur_1.5", lambda img: add_gaussian_blur(img, 1.5)),
        ("contrast_0.25", lambda img: scale_contrast(img, 0.25)),
        ("contrast_0.50", lambda img: scale_contrast(img, 0.50)),
        ("illum_grad", lambda img: add_illumination_gradient(img, "horizontal", 0.3)),
    ]

    for p in patches:
        print(f"\n  Image: {p['name']}")
        for deg_name, deg_fn in degradations:
            np.random.seed(42)
            degraded = deg_fn(p['image'])
            for method in methods:
                n_trials = N_TRIALS if "Q" in method or "NEQR" in method else 1
                agg = run_trials(degraded, p['mask'], method, n_trials)
                agg['image'] = p['name']
                agg['degradation'] = deg_name
                results.append(agg)
            best = max(results[-4:], key=lambda r: r['f1_exact_mean'])
            print(f"    {deg_name:<15} best={best['method']:<15} F1={best['f1_exact_mean']:.4f}")

    save_results(results, "exp4_image_degradation.csv")
    return results


def experiment_5():
    """Experiment 5 -- Quantum Hardware Noise Simulation"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 5: Quantum Noise Simulation")
    print("=" * 60)

    patches = load_synthetic_patches(8)[:2]
    noise_configs = get_experiment_noise_configs()
    results = []

    for p in patches:
        print(f"\n  Image: {p['name']}")
        for noise_name, noise_model in noise_configs:
            for method in ["QPIE-QHED", "NEQR-Gradient"]:
                try:
                    agg = run_trials(p['image'], p['mask'], method, N_TRIALS,
                                     DEFAULT_SHOTS, noise_model)
                    agg['image'] = p['name']
                    agg['noise'] = noise_name
                    results.append(agg)
                    print(f"    {noise_name:<15} {method:<15} F1={agg['f1_exact_mean']:.4f}")
                except Exception as e:
                    print(f"    {noise_name:<15} {method:<15} ERROR: {e}")

    save_results(results, "exp5_noise_simulation.csv")
    return results


def experiment_8():
    """Experiment 8 -- SomBench Real Lunar Benchmark"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 8: SomBench Real Lunar Benchmark")
    print("=" * 60)

    results = []
    methods = ["Sobel", "Canny", "Robinson", "QPIE-QHED", "NEQR-Gradient"]

    for size in [8, 16]:
        patches = load_sombench_patches(size)
        if not patches:
            print(f"  No {size}x{size} SomBench patches with edges")
            continue

        print(f"\n  {size}x{size}: {len(patches)} patches")

        for p in patches:
            for method in methods:
                n_trials = N_TRIALS if "Q" in method or "NEQR" in method else 1
                try:
                    agg = run_trials(p['image'], p['mask'], method, n_trials)
                    agg['patch'] = p['name']
                    agg['size'] = size
                    results.append(agg)
                except Exception as e:
                    print(f"    ERROR: {p['name']} {method}: {e}")

        for method in methods:
            mr = [r for r in results if r['method'] == method and r.get('size') == size]
            if mr:
                mean_f1 = np.mean([r['f1_exact_mean'] for r in mr])
                print(f"    {method:<15} Mean F1={mean_f1:.4f} (n={len(mr)})")

    save_results(results, "exp8_sombench_benchmark.csv")
    return results


def experiment_3():
    """Experiment 3 -- Resolution Scaling (4x4 only, 8x8 already in Exp 1)"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 3: Resolution Scaling")
    print("=" * 60)

    results = []
    for size in [4, 8]:
        patches = load_synthetic_patches(size)
        if not patches:
            continue

        print(f"\n  Resolution: {size}x{size} ({len(patches)} images)")
        methods = ["Sobel", "Robinson", "QPIE-QHED", "NEQR-Gradient"]

        for p in patches[:3]:
            for method in methods:
                n_trials = N_TRIALS if "Q" in method or "NEQR" in method else 1
                start = time.time()
                agg = run_trials(p['image'], p['mask'], method, n_trials)
                elapsed = time.time() - start
                agg['image'] = p['name']
                agg['size'] = size
                agg['time_sec'] = elapsed
                results.append(agg)
                print(f"    {p['name']:<20} {method:<15} F1={agg['f1_exact_mean']:.4f} t={elapsed:.1f}s")

    save_results(results, "exp3_resolution_scaling.csv")
    return results


# ============================================================

def generate_summary():
    """Generate summary of all experiment results."""
    print("\n" + "=" * 70)
    print("FINAL RESULTS SUMMARY")
    print("=" * 70)

    csv_files = sorted(RESULTS_DIR.glob("exp*.csv"))
    print(f"\n  Result files generated: {len(csv_files)}")
    for f in csv_files:
        # Count rows
        with open(f) as fh:
            n_rows = sum(1 for _ in fh) - 1
        print(f"    {f.name}: {n_rows} rows")

    print("\n" + "=" * 70)
    print("All experiments complete!")
    print("=" * 70)


def main():
    np.random.seed(42)
    total_start = time.time()

    print("=" * 60)
    print("REMAINING EXPERIMENTS RUNNER")
    print("=" * 60)

    experiment_5()   # Noise simulation (fixed)
    experiment_4()   # Image degradation
    experiment_8()   # SomBench benchmark
    experiment_3()   # Resolution scaling

    generate_summary()

    total_time = time.time() - total_start
    print(f"\nTotal time: {total_time/60:.1f} minutes")


if __name__ == "__main__":
    main()
