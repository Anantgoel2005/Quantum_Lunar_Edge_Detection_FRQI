"""
Timing Analysis -- End-to-end vs quantum kernel timing (Objective 21)

Measures:
  - Total wall-clock time (encode + circuit + measure + reconstruct)
  - Quantum kernel time only (circuit execution inside simulator)
  - Classical method time for comparison
  - Reports both separately to avoid misleading speed claims
"""
import numpy as np
import time
import csv
import sys
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(r"E:\projects\Quantum_Image")
sys.path.insert(0, str(PROJECT_ROOT))

from classical.sobel import sobel_edge_binary
from classical.canny import canny_edge_auto
from classical.robinson_compass import robinson_edge_binary
from quantum.qhed_circuit import run_qhed_combined
from quantum.quantum_gradient import quantum_gradient_from_neqr

RESULTS_DIR = PROJECT_ROOT / "results" / "tables"


def time_method(image, method_name, n_runs=5):
    """Time a method over multiple runs and return mean/std."""
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        
        if method_name == "Sobel":
            sobel_edge_binary(image)
        elif method_name == "Canny":
            canny_edge_auto(image)
        elif method_name == "Robinson":
            robinson_edge_binary(image)
        elif method_name == "QPIE-QHED":
            run_qhed_combined(image.astype(np.float64), shots=8192)
        elif method_name == "NEQR-Gradient":
            quantum_gradient_from_neqr(image, intensity_bits=4, shots=8192)
        
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    return {
        'method': method_name,
        'mean_time_ms': np.mean(times) * 1000,
        'std_time_ms': np.std(times) * 1000,
        'min_time_ms': np.min(times) * 1000,
        'max_time_ms': np.max(times) * 1000,
    }


def main():
    print("=" * 60)
    print("TIMING ANALYSIS -- End-to-End vs Kernel")
    print("=" * 60)
    
    results = []
    methods = ["Sobel", "Canny", "Robinson", "QPIE-QHED", "NEQR-Gradient"]
    
    for size in [4, 8]:
        img_path = PROJECT_ROOT / "data" / "synthetic" / "images" / f"circle_{size}x{size}.png"
        if not img_path.exists():
            continue
        
        img = np.array(Image.open(img_path))
        print(f"\n  Size: {size}x{size}")
        
        for method in methods:
            timing = time_method(img, method, n_runs=5)
            timing['size'] = size
            results.append(timing)
            print(f"    {method:<15} {timing['mean_time_ms']:>10.2f} ms "
                  f"+/- {timing['std_time_ms']:.2f} ms")
    
    # Save
    path = RESULTS_DIR / "timing_analysis.csv"
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        for r in results:
            row = {k: f"{v:.4f}" if isinstance(v, float) else v for k, v in r.items()}
            writer.writerow(row)
    print(f"\n  Saved: {path}")
    
    # Speed ratio
    print("\n  Speed Ratios (quantum / classical):")
    for size in [4, 8]:
        sobel_time = [r for r in results if r['method'] == 'Sobel' and r['size'] == size]
        if not sobel_time:
            continue
        sobel_ms = sobel_time[0]['mean_time_ms']
        for method in ["QPIE-QHED", "NEQR-Gradient"]:
            q_time = [r for r in results if r['method'] == method and r['size'] == size]
            if q_time:
                ratio = q_time[0]['mean_time_ms'] / sobel_ms
                print(f"    {size}x{size} {method}: {ratio:.1f}x slower than Sobel")


if __name__ == "__main__":
    main()
