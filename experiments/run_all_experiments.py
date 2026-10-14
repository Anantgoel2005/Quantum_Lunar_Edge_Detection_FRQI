"""
Master Experiment Runner -- Executes all experiments from PROJECT_SUMMARY.md

Experiments:
  1. Representation Ablation (QPIE-QHED vs NEQR-Gradient)
  2. Shot Count Sensitivity
  3. Resolution Scaling
  4. Image Quality Degradation (noise, blur, contrast, illumination)
  5. Quantum Hardware Noise Simulation
  6. Synthetic Edge Geometry Ablation
  7. Preprocessing Strategy
  8. SomBench Real Lunar Benchmark
  9. Resource Scaling Analysis
  10. Failure Taxonomy

Each experiment:
  - 10 trials per configuration
  - Reports mean +/- std
  - Saves results to CSV
"""
import numpy as np
import csv
import sys
import time
from pathlib import Path
from collections import defaultdict
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from classical.finite_difference import forward_gradient, quantized_gradient
from classical.sobel import sobel_edge, sobel_edge_binary
from classical.canny import canny_edge_auto
from classical.robinson_compass import robinson_edge_binary
from evaluation.metrics import boundary_f1, compute_all_metrics
from quantum.qhed_circuit import run_qhed, run_qhed_combined
from quantum.quantum_gradient import quantum_gradient_from_neqr
from quantum.noise_models import get_noise_model, get_experiment_noise_configs

RESULTS_DIR = PROJECT_ROOT / "results" / "corrected" / "tables"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
N_TRIALS = 10
DEFAULT_SHOTS = 8192


def load_synthetic_patches(size=8):
    """Load all synthetic images and masks of a given size."""
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
    """Load stratified-sampled SomBench patches and masks."""
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


def run_quantum_qhed(image, shots, noise_model=None, seed_simulator=None):
    """Run QPIE+QHED and return binary edge map + continuous map."""
    combined, h_map, v_map = run_qhed_combined(
        image.astype(np.float64), shots=shots, noise_model=noise_model, seed_simulator=seed_simulator
    )
    # Threshold at median of non-zero values
    nonzero = combined[combined > 0]
    if len(nonzero) > 0:
        thresh = np.median(nonzero)
    else:
        thresh = 0.5
    binary = (combined >= thresh).astype(np.uint8) * 255
    continuous = combined
    return binary, continuous


def run_quantum_neqr(image, shots, noise_model=None, seed_simulator=None):
    """Run NEQR+Gradient and return binary edge map + continuous map."""
    edge_map, recon, qc = quantum_gradient_from_neqr(
        image, intensity_bits=4, shots=shots, noise_model=noise_model, seed_simulator=seed_simulator
    )
    nonzero = edge_map[edge_map > 0]
    if len(nonzero) > 0:
        thresh = np.median(nonzero)
    else:
        thresh = 0.5
    binary = (edge_map >= thresh).astype(np.uint8) * 255
    continuous = edge_map
    return binary, continuous


def evaluate_method(image, mask, method, shots=DEFAULT_SHOTS, noise_model=None, seed_simulator=None):
    """Run a single method and return metrics dict."""
    if method == "Sobel":
        binary, continuous = sobel_edge_binary(image)
        continuous = sobel_edge(image)
    elif method == "Canny":
        binary = canny_edge_auto(image)
        continuous = binary
    elif method == "Robinson":
        binary, continuous, _ = robinson_edge_binary(image)
    elif method == "QPIE-QHED":
        binary, continuous = run_quantum_qhed(image, shots, noise_model, seed_simulator)
    elif method == "NEQR-Gradient":
        binary, continuous = run_quantum_neqr(image, shots, noise_model, seed_simulator)
    elif method in ("Forward-Gradient", "Quantized-Gradient"):
        continuous = forward_gradient(image) if method == "Forward-Gradient" else quantized_gradient(image)
        positive = continuous[continuous > 0]
        threshold = np.median(positive) if len(positive) else 0.5
        binary = (continuous >= threshold).astype(np.uint8) * 255
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return compute_all_metrics(binary, continuous, mask, method)


def run_trials(image, mask, method, n_trials=N_TRIALS, shots=DEFAULT_SHOTS, noise_model=None):
    """Run multiple trials and return mean/std metrics."""
    results = []
    for t in range(n_trials):
        m = evaluate_method(image, mask, method, shots, noise_model, seed_simulator=42 + t)
        results.append(m)
    
    # Aggregate
    keys = ['f1_exact', 'f1_1px', 'f1_2px', 'precision_exact', 'recall_exact', 'iou', 'chamfer', 'pr_auc']
    agg = {'method': method}
    for k in keys:
        values = [r[k] for r in results]
        agg[f'{k}_mean'] = np.mean(values)
        agg[f'{k}_std'] = np.std(values)
    return agg


def save_results(results, filename, extra_fields=None):
    """Save results list to CSV."""
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
# EXPERIMENT IMPLEMENTATIONS
# ============================================================

def experiment_1():
    """Experiment 1 -- Representation Ablation (Core Experiment)"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 1: Representation Ablation")
    print("  QPIE+QHED vs NEQR+Gradient on same images")
    print("=" * 60)
    
    patches = load_synthetic_patches(8)
    methods = ["Sobel", "Canny", "Robinson", "Forward-Gradient", "Quantized-Gradient", "QPIE-QHED", "NEQR-Gradient"]
    results = []
    
    for p in patches:
        print(f"\n  Image: {p['name']} ({p['size']}x{p['size']})")
        for method in methods:
            n_trials = N_TRIALS if "Q" in method or "NEQR" in method else 1
            agg = run_trials(p['image'], p['mask'], method, n_trials)
            agg['image'] = p['name']
            agg['size'] = p['size']
            results.append(agg)
            print(f"    {method:<15} F1={agg['f1_exact_mean']:.4f} +/- {agg.get('f1_exact_std',0):.4f}")
    
    save_results(results, "exp1_representation_ablation.csv")
    return results


def experiment_2():
    """Experiment 2 -- Shot Count Sensitivity"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 2: Shot Count Sensitivity")
    print("=" * 60)
    
    patches = load_synthetic_patches(8)[:3]  # Use 3 images
    shot_counts = [256, 512, 1024, 2048, 4096, 8192, 16384]
    methods = ["QPIE-QHED", "NEQR-Gradient"]
    results = []
    
    for p in patches:
        print(f"\n  Image: {p['name']}")
        for shots in shot_counts:
            for method in methods:
                agg = run_trials(p['image'], p['mask'], method, N_TRIALS, shots)
                agg['image'] = p['name']
                agg['shots'] = shots
                results.append(agg)
                print(f"    shots={shots:<6} {method:<15} F1={agg['f1_exact_mean']:.4f}")
    
    save_results(results, "exp2_shot_sensitivity.csv")
    return results


def experiment_3():
    """Experiment 3 -- Resolution Scaling"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 3: Resolution Scaling")
    print("=" * 60)
    
    results = []
    for size in [4, 8, 16]:
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
                agg = run_trials(p['image'], p['mask'], method, N_TRIALS, 
                               DEFAULT_SHOTS, noise_model)
                agg['image'] = p['name']
                agg['noise'] = noise_name
                results.append(agg)
                print(f"    {noise_name:<15} {method:<15} F1={agg['f1_exact_mean']:.4f}")
    
    save_results(results, "exp5_noise_simulation.csv")
    return results


def experiment_6():
    """Experiment 6 -- Synthetic Edge Geometry Ablation"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 6: Geometry Ablation")
    print("=" * 60)
    
    patches = load_synthetic_patches(8)
    methods = ["Sobel", "Canny", "Robinson", "Forward-Gradient", "Quantized-Gradient", "QPIE-QHED", "NEQR-Gradient"]
    results = []
    
    for p in patches:
        print(f"\n  Geometry: {p['name']}")
        for method in methods:
            n_trials = N_TRIALS if "Q" in method or "NEQR" in method else 1
            agg = run_trials(p['image'], p['mask'], method, n_trials)
            agg['geometry'] = p['name']
            results.append(agg)
            print(f"    {method:<15} F1={agg['f1_exact_mean']:.4f} +/- {agg.get('f1_exact_std',0):.4f}")
    
    save_results(results, "exp6_geometry_ablation.csv")
    return results


def experiment_8():
    """Experiment 8 -- SomBench Real Lunar Benchmark"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 8: SomBench Real Lunar Benchmark")
    print("=" * 60)
    
    results = []
    for size in [8, 16]:
        patches = load_sombench_patches(size)
        if not patches:
            print(f"  No {size}x{size} SomBench patches with edges")
            continue
        
        print(f"\n  {size}x{size}: {len(patches)} patches")
        methods = ["Sobel", "Canny", "Robinson", "Forward-Gradient", "Quantized-Gradient", "QPIE-QHED", "NEQR-Gradient"]
        
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
        
        # Print summary
        for method in methods:
            method_results = [r for r in results if r['method'] == method and r.get('size') == size]
            if method_results:
                mean_f1 = np.mean([r['f1_exact_mean'] for r in method_results])
                print(f"    {method:<15} Mean F1={mean_f1:.4f} (n={len(method_results)})")
    
    save_results(results, "exp8_sombench_benchmark.csv")
    return results


def experiment_9():
    """Primitive preparation and operation costs, separately for every pass."""
    from qiskit import transpile
    from quantum.qhed_circuit import build_qhed_circuit
    from quantum.neqr_encoder import neqr_encode_simplified
    rng = np.random.default_rng(42)
    results = []
    for size in [4, 8]:
        image = rng.integers(30, 200, (size, size), dtype=np.uint8)
        circuits = []
        for direction in ['horizontal', 'vertical']:
            for offset in [0, 1]:
                qc, _, _ = build_qhed_circuit(image, direction, offset)
                circuits.append(('QPIE-QHED', f'{direction}_{offset}', qc, 4))
        qc, _, _ = neqr_encode_simplified(image, intensity_bits=4)
        qc.measure_all()
        circuits.append(('NEQR-Gradient', 'hybrid_reconstruction', qc, 1))
        for method, circuit_pass, qc, circuits_per_trial in circuits:
            compiled = transpile(qc, basis_gates=['u', 'cx'], seed_transpiler=42)
            counts = compiled.count_ops()
            results.append({'method': method, 'size': size, 'circuit_pass': circuit_pass,
                'n_qubits': qc.num_qubits, 'circuit_depth': compiled.depth(),
                'cx_count': counts.get('cx', 0), 'u_count': counts.get('u', 0),
                'circuits_per_trial': circuits_per_trial, 'basis': 'u,cx'})
    save_results(results, 'exp9_resource_scaling.csv')
    return results


# ============================================================
# MAIN
# ============================================================

def main():
    np.random.seed(SEED)
    
    print("=" * 60)
    print("QUANTUM IMAGE EDGE DETECTION -- EXPERIMENT RUNNER")
    print("=" * 60)
    print(f"Trials per config: {N_TRIALS}")
    print(f"Default shots: {DEFAULT_SHOTS}")
    print(f"Random seed: {SEED}")
    
    total_start = time.time()
    
    # Run experiments in order of computational cost
    experiment_9()   # Resource scaling (fast, no simulation)
    experiment_1()   # Core ablation
    experiment_6()   # Geometry ablation
    experiment_2()   # Shot sensitivity
    experiment_5()   # Noise simulation
    experiment_8()   # SomBench benchmark
    experiment_3()   # Resolution scaling
    
    total_time = time.time() - total_start
    
    print("\n" + "=" * 60)
    print(f"ALL EXPERIMENTS COMPLETE in {total_time/60:.1f} minutes")
    print(f"Results saved to: {RESULTS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
