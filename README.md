# Quantum Lunar Edge Detection

### A Comparative Study of Two Quantum Representations and Classical Methods on Grayscale Lunar Crater Images

---

> **Project Type:** Quantum Image Processing Research  
> **Domain:** Quantum Computing × Planetary Image Analysis  
> **Tools:** Python · Qiskit · Qiskit Aer · OpenCV · NumPy · Matplotlib  
> **Primary Dataset:** NASA-IBM SomBench WAC Lunar Crater Dataset  
> **Hardware:** Local CPU simulation via Qiskit AerSimulator (ideal + noisy)

---

## Overview

This project implements and compares two fundamentally different quantum edge detection pipelines against classical baselines for lunar crater rim detection:

| Pipeline | Encoding | Edge Operation | Qubits (8×8) |
|----------|----------|---------------|---------------|
| **QPIE + QHED** | Amplitude encoding | Hadamard interference | 6 |
| **NEQR + Gradient** | Basis-state encoding | Quantum gradient | 8 |
| **Sobel** (classical) | N/A | 3×3 convolution | N/A |
| **Canny** (classical) | N/A | Multi-stage NMS | N/A |
| **Robinson Compass** (classical) | N/A | 8-directional masks | N/A |

## Key Results

| Method | Synthetic F1 | Real Lunar F1 | Speed vs Sobel |
|--------|:-----------:|:------------:|:--------------:|
| **Sobel** | **0.874** | **0.285** | 1× |
| **Robinson** | 0.866 | 0.283 | 2× |
| Canny | 0.686 | 0.086 | 3× |
| **NEQR-Gradient** | 0.464 | 0.262 | 3,191× slower |
| QPIE-QHED | 0.090 | 0.160 | 5,438× slower |

### Core Findings

1. **Classical methods outperform quantum** at current simulation scales
2. **NEQR-Gradient is the stronger quantum approach** — 5× better F1 than QPIE-QHED
3. **The gap narrows on real noisy lunar data** — NEQR (0.262) approaches Sobel (0.285)
4. **QPIE-QHED fails completely on 3/8 geometries** due to the measurement bottleneck
5. **Quantum methods produce unique uncertainty maps** from measurement statistics

## Project Structure

```
├── classical/              # Sobel, Canny, Robinson Compass edge detectors
├── quantum/                # QPIE encoder, QHED circuit, NEQR encoder, quantum gradient
├── preprocessing/          # Image loader, augmentor, preprocessor, annotation rasteriser
├── evaluation/             # Boundary F1, precision, recall, IoU, Chamfer, PR-AUC
├── experiments/            # All 10 experiment runners + analysis + report generator
├── data/
│   ├── synthetic/          # 17 synthetic image-mask pairs (8 geometries × 2 sizes)
│   └── sombench/           # Stratified-sampled SomBench patches + GT masks
├── results/
│   ├── tables/             # 13 CSV result files
│   └── figures/            # 9 PNG visualization figures
├── report/                 # Final results report
├── PROJECT_SUMMARY.md      # Full project blueprint (all 23 objectives ✓)
└── requirements.txt        # Python dependencies
```

## Experiments (All 10 Complete)

| # | Experiment | Key Finding |
|---|-----------|-------------|
| 1 | Representation Ablation | Classical >> NEQR >> QPIE-QHED |
| 2 | Shot Count Sensitivity | Converges above 512 shots |
| 3 | Resolution Scaling | NEQR better at 4×4 than 8×8 |
| 4 | Image Quality Degradation | Classical robust to noise; quantum stable to contrast |
| 5 | Quantum Noise Simulation | Hardware noise surprisingly helps QPIE-QHED slightly |
| 6 | Geometry Ablation | NEQR excels on diagonals (F1=0.80) |
| 7 | Preprocessing Strategy | CLAHE/gamma don't improve quantum methods |
| 8 | SomBench Benchmark | NEQR competitive with Sobel on real lunar patches |
| 9 | Resource Scaling | Circuit depth analysis for both approaches |
| 10 | Failure Taxonomy | QPIE: 3 complete misses + 4 displacements; NEQR: 4 successes |

## Dataset

**SomBench WAC Crater Detection** (NASA-IBM):
- 200 images downloaded (test + val splits)
- 29 stratified-sampled across 10 condition categories
- 8×8 and 16×16 patches extracted with COCO polygon rim masks as ground truth

**Synthetic Ground Truth:**
- 8 geometry types: horizontal line, vertical line, diagonal, corner, circle, ellipse, multiple circles, irregular curve
- Exact analytic edge masks for precise evaluation

## Installation

```bash
pip install -r requirements.txt
```

### Dependencies
- Python 3.10+
- Qiskit ≥ 1.0
- Qiskit Aer ≥ 0.14
- OpenCV ≥ 4.9
- NumPy, SciPy, Matplotlib, scikit-learn, Pillow, tifffile, imagecodecs

## Running

```bash
# Generate synthetic dataset
python data/synthetic/generator.py

# Run Phase 1 (classical baselines + dataset curation)
python experiments/phase1_pipeline.py

# Run all quantum experiments
python experiments/run_all_experiments.py
python experiments/run_remaining_experiments.py
python experiments/run_exp7_exp10.py

# Timing analysis & confidence maps
python experiments/timing_analysis.py
python experiments/confidence_maps.py

# Generate analysis figures and final report
python experiments/analysis.py
python experiments/generate_report.py
```

## License

This project is for academic research purposes.

## Author

Samradh Sahni
