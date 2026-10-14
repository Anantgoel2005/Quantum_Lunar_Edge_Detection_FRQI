# Quantum Edge Detection Under Changing Image Conditions

> **Implementation correction, 14 October 2026:** This document preserves the original research plan and historical claims. See `README.md` and `report/fixes_and_validation.md` for the corrected implementation and validation. NEQR currently uses quantum encoding and measurement followed by a **classical** gradient; a coherent quantum gradient remains a research objective. Original tables and figures are historical; new outputs are under `results/corrected/`.
### A Comparative Study of Two Quantum Representations and Classical Methods on Grayscale Lunar Crater Images

---

> **Project Type:** Quantum Image Processing Research
> **Domain:** Quantum Computing x Planetary Image Analysis
> **Tools:** Python . Qiskit . Qiskit Aer . OpenCV . NumPy . Matplotlib . scikit-image . Streamlit (optional)
> **Primary Dataset:** NASA-IBM SomBench WAC Lunar Crater Dataset
> **Secondary Dataset:** NASA LRO WAC/NAC Grayscale Tiles
> **Validation Dataset:** MNIST (circuit debugging only)
> **Image Type:** Grayscale only
> **Hardware:** Local CPU simulation via Qiskit AerSimulator (ideal + noisy)

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Research Questions](#2-research-questions)
3. [Aim and Objectives](#3-aim-and-objectives)
4. [Use Case and Motivation](#4-use-case-and-motivation)
5. [Background and Theory](#5-background-and-theory)
6. [System Architecture](#6-system-architecture)
7. [Methodology](#7-methodology)
8. [Experimental Design](#8-experimental-design)
9. [Hypotheses](#9-hypotheses)
10. [Evaluation Metrics](#10-evaluation-metrics)
11. [Project Timeline](#11-project-timeline)
12. [Tech Stack and Dependencies](#12-tech-stack-and-dependencies)
13. [Directory Structure](#13-directory-structure)
14. [Optional Extensions](#14-optional-extensions)
15. [References](#15-references)

---

## 1. Problem Statement

Edges in images correspond to significant intensity transitions between neighbouring pixels, marking object boundaries and structural features. In planetary science, accurate edge detection in grayscale lunar imagery is critical for identifying crater rim boundaries, terrain elevation changes, and surface morphology -- all of which are essential inputs for autonomous rover navigation, geological age dating, and safe crewed landing zone selection.

Classical edge detection methods such as Sobel filtering and Canny edge detection are well-established and computationally efficient. As quantum computing technology matures, it becomes important to understand how different quantum image representations and quantum operations apply to this fundamental image-processing task -- and critically, whether the choice of representation itself influences the quality and robustness of the resulting edge information.

Two distinct approaches exist for encoding a grayscale image into a quantum state:

- **QPIE-based encoding** (used in the canonical QHED algorithm by Yao et al., 2017) encodes pixel intensities as probability amplitudes in a superposition state. The Quantum Hadamard Edge Detection (QHED) algorithm then applies a Hadamard operation over this amplitude-encoded representation to extract edges through quantum interference.

- **NEQR encoding** stores the exact binary value of each pixel intensity in the computational basis of a dedicated intensity register. A separate quantum gradient or Sobel-style operator must be applied to extract edge information from this basis-state representation.

These two approaches are fundamentally different in their state preparation, circuit structure, qubit requirements, and sensitivity to noise. No published work has systematically compared them for edge detection on planetary surface imagery.

This project implements both quantum approaches as independent pipelines, benchmarks them against classical Sobel and Canny baselines, and systematically investigates how image characteristics, preprocessing choices, measurement parameters, and quantum hardware noise influence each method's performance -- with lunar crater rim detection as the primary application domain.

---

## 2. Research Questions

### Primary Research Question

> **"Does the choice of quantum image representation -- QPIE amplitude encoding (QHED) versus NEQR basis-state encoding -- significantly affect the quality, robustness, and resource cost of quantum edge detection on grayscale lunar crater imagery?"**

### Sub-Questions

| # | Sub-Question |
|---|-------------|
| Q1 | How does image resolution (4x4, 8x8, 16x16) affect edge quality and resource cost for each representation? |
| Q2 | How does measurement shot count influence statistical variance and quality of reconstructed edge maps? |
| Q3 | How does edge geometry (straight lines, diagonals, circles, ellipses) affect each method, given identical image conditions? |
| Q4 | How do increasing levels of image noise (Gaussian, blur, contrast, illumination) degrade each method? |
| Q5 | How does quantum hardware noise (depolarizing, readout, gate noise) affect each method when simulated on noisy AerSimulator? |
| Q6 | Does preprocessing (Gaussian, median, CLAHE, gamma) improve quantum edge detection on lunar crater patches? |
| Q7 | Do the two quantum representations exhibit different failure modes? |
| Q8 | What is the true end-to-end runtime cost compared with classical baselines? |

---

## 3. Aim and Objectives

### Aim

To implement two independent quantum edge detection pipelines -- QPIE amplitude encoding with QHED, and NEQR basis-state encoding with a quantum gradient operator -- and systematically compare their performance, robustness, and resource requirements against classical Sobel and Canny methods on grayscale lunar crater images, under a controlled set of image and quantum processing conditions.

### Objectives

| # | Objective | Status |
|---|-----------|--------|
| 1 | Understand image gradients, edge theory, and classical edge detection | [x] |
| 2 | Implement Sobel and Canny edge detection using OpenCV | [x] |
| 3 | Understand QPIE amplitude encoding and the canonical QHED circuit | [x] |
| 4 | Implement QPIE + QHED pipeline in Qiskit | [x] |
| 5 | Understand NEQR basis-state encoding and quantum gradient operators | [x] |
| 6 | Implement NEQR + coherent quantum gradient pipeline in Qiskit (hybrid currently implemented) | [ ] |
| 7 | Set up Qiskit AerSimulator in ideal and noisy modes | [x] |
| 8 | Build synthetic ground truth dataset (lines, corners, circles, ellipses) | [x] |
| 9 | Download and preprocess SomBench WAC Lunar Crater dataset | [x] |
| 10 | Implement evaluation metrics: boundary F1 (tolerance-based), P, R, IoU, Chamfer, PR-AUC | [x] |
| 11 | Run Experiment 1: Representation ablation (QPIE-QHED vs NEQR-Gradient, all else fixed) | [x] |
| 12 | Run Experiment 2: Resolution scaling (4x4, 8x8, 16x16) | [x] |
| 13 | Run Experiment 3: Shot count sensitivity with repeated trials (n=10) | [x] |
| 14 | Run Experiment 4: Image noise and degradation robustness | [x] |
| 15 | Run Experiment 5: Quantum hardware noise simulation | [x] |
| 16 | Run Experiment 6: Synthetic edge geometry ablation | [x] |
| 17 | Run Experiment 7: Preprocessing strategy comparison | [x] |
| 18 | Run Experiment 8: Real lunar crater benchmark (SomBench) | [x] |
| 19 | Run Experiment 9: Detailed resource scaling analysis | [x] |
| 20 | Run Experiment 10: Failure analysis and failure taxonomy | [x] |
| 21 | Report end-to-end timing vs quantum kernel timing separately | [x] |
| 22 | Produce confidence/uncertainty maps from quantum probability outputs | [x] |
| 23 | Compile results, draw conclusions, write final report | [x] |

---

## 4. Use Case and Motivation

### Primary Use Case: Lunar Crater Rim Edge Detection

**Primary Dataset:** NASA-IBM SomBench WAC Lunar Crater Detection Dataset
**Access:** HuggingFace / IBM Research (open, free)
**Full Dataset Size:** ~964,000 WAC tiles total; Crater Detection Benchmark: 1,000 images (800 train / 100 val / 100 test)
**Description:** Single-band LROC WAC grayscale lunar tiles at 512x512 pixels (~100 m/px). Crater annotations stored as polygons in COCO format -- rasterisable to pixel-level crater rim masks. Includes illumination metadata (incidence angle, emission angle). Annotations based on the Robbins crater catalog.

**Secondary Dataset:** NASA LRO (qualitative validation only)

**Note on LU3M6T (Kaggle):** LU3M6T provides YOLOv5 bounding-box labels -- NOT pixel-level rim masks. Not suitable as quantitative ground truth. May be used optionally for supplementary context only.

**MNIST:** Circuit debugging and development validation ONLY. Not used for scientific comparison.

### Dataset Curation Strategy: Stratified Sampling

Quantum circuit simulation is computationally expensive -- each 8x8 patch takes seconds per trial, and each configuration requires 10 repeated trials. Running all 1,000 SomBench images is unnecessary and infeasible. Instead, we use **stratified sampling** to curate a representative subset of 30 patches that covers the full range of real lunar imaging conditions.

**Procedure:**
```
Step 1: Download full SomBench WAC crater detection benchmark (~1,000 images)
Step 2: Browse and analyse each image for key characteristics:
          - Contrast level (low / medium / high)
          - Illumination angle (from SomBench incidence angle metadata)
          - Crater rim size relative to patch (small / medium / large)
          - Terrain complexity (flat / rough / overlapping craters)
Step 3: Hand-pick 30 representative patches using stratified sampling
Step 4: Extract 8x8 and 16x16 patches from each selected image
Step 5: Rasterise COCO polygon annotations to pixel-level ground truth masks
Step 6: Run ALL methods (Sobel, Canny, Robinson, QPIE-QHED, NEQR-Gradient)
        on these same 30 patches across all experiments
Step 7: Store all results (CSV tables + figures) and compare
```

**30-Image Stratified Breakdown:**

| Category | Condition | Count | Purpose |
|----------|-----------|-------|---------|
| Contrast | Low contrast crater rim | 3 | Tests H4 (low contrast → lower F1?) |
| Contrast | Medium contrast | 3 | Baseline comparison |
| Contrast | High contrast | 3 | Best-case scenario |
| Illumination | Low incidence angle (soft shadows) | 3 | Gentle, diffuse edges |
| Illumination | High incidence angle (harsh shadows) | 3 | Strong directional lighting |
| Illumination | Mixed / variable illumination | 3 | Real-world conditions |
| Crater size | Small crater rim in patch | 3 | Thin circular edges |
| Crater size | Large crater rim in patch | 3 | Thick, well-defined edges |
| Terrain | Clean crater on flat terrain | 3 | Easy case (isolated crater) |
| Terrain | Overlapping craters / rough terrain | 3 | Hard case (complex boundaries) |
| **Total** | | **30** | |

**Why stratified sampling is stronger than random sampling:**
```
Stratified (this approach):
  ✓ Every condition category is guaranteed to be represented
  ✓ You can make claims about performance under EACH condition
  ✓ Reviewers can see exactly WHY each image was chosen
  ✓ Results are reproducible (same 30 images in every experiment)

Random sampling (avoided):
  ✗ Might get 25 high-contrast + 5 low-contrast by chance
  ✗ Cannot make statistically valid claims about low-contrast performance
  ✗ No principled answer to "why these 30?"
```

**Total compute estimate:**
```
Quantum runs:   30 patches × 2 methods × 10 trials = 600 circuit executions
Classical runs: 30 patches × 3 methods = 90 runs (instant)
+ Degradation experiments on subsets
+ Synthetic geometry experiments (separate)

Estimated total: ~5,000-10,000 circuit runs across all experiments
Estimated time:  Several hours on a standard laptop (feasible)
```

### Why Lunar Craters

- **Mission-critical:** Crater boundary detection is essential for safe autonomous rover navigation
- **Geological dating:** Crater size-frequency distribution is the primary method for dating surface regions
- **Illumination variability:** Sun angle dramatically changes crater edge contrast -- natural robustness testbed
- **Circular geometry:** Crater rims are dominantly circular -- a unique challenge for H/V quantum gradient operators
- **Natively grayscale:** No RGB conversion artefacts
- **Unexplored domain:** Zero published quantum image processing papers on planetary surface imagery

### Ground Truth Methodology

```
Ground Truth Sources (independent of classical baselines):

  Source 1: Synthetic exact edges
    - Programmatically generated with known edge positions
    - Exact pixel-level reference masks available analytically

  Source 2: SomBench COCO polygon annotations
    - Independent NASA-IBM expert annotations
    - Rasterised to pixel-level binary edge masks

IMPORTANT: Classical Sobel and Canny are BASELINES, not ground truth.

  Correct scientific claim:
    "QPIE-QHED achieves F1 = 0.XX against the independent
     reference mask, compared with Sobel F1 = 0.XX and Canny F1 = 0.XX."

  Incorrect claim (avoided):
    "Quantum is 82% similar to Canny."
```

---

## 5. Background and Theory

### 5.1 Classical Edge Detection

**Image Gradient:**
```
G = sqrt(Gx^2 + Gy^2)
Gx = dI/dx  (horizontal gradient)
Gy = dI/dy  (vertical gradient)
```

**Sobel Filter (3x3):**
```
Kx = [[-1, 0, +1],    Ky = [[-1, -2, -1],
      [-2, 0, +2],          [ 0,  0,  0],
      [-1, 0, +1]]          [+1, +2, +1]]
```

**Canny:** Gaussian -> Sobel -> Non-max suppression -> Double threshold -> Hysteresis

**Robinson Compass Operator (Robinson, 1977):**
A directional edge detector using eight 3x3 masks corresponding to the eight compass directions:
```
Directions: 0, 45, 90, 135, 180, 225, 270, 315 degrees

Example -- 0-degree mask (East, strong horizontal-edge response):
  K_0 = [[-1,  0, +1],
         [-2,  0, +2],
         [-1,  0, +1]]

The remaining seven masks are generated by rotating K_0 in 45-degree steps.

For each direction k, compute the directional response:
  R_k(x,y) = I * K_k

Edge strength and dominant direction:
  E(x,y) = max_k |R_k(x,y)|          (edge magnitude)
  D(x,y) = argmax_k |R_k(x,y)|       (dominant direction, in degrees)
```

Why Robinson is particularly valuable for THIS project:
```
Your Experiment 6 asks: Does edge GEOMETRY affect quantum performance?

Robinson provides a direction-aware classical reference for each geometry:

  Horizontal edge  ->  Robinson 0 / 180  ->  strong response
  Vertical edge    ->  Robinson 90 / 270 ->  strong response
  45-deg diagonal  ->  Robinson 45 / 225 ->  strong response
  Circle / ellipse ->  All 8 directions rotate around rim

This allows you to diagnose FAILURES specifically:
  If QPIE-QHED F1 drops on diagonal edges but
  Robinson 45-deg responds strongly -> the failure is
  quantum-specific, not a property of the image itself.

  If Robinson also struggles -> the image content is
  genuinely difficult, not a quantum limitation.

Robinson dominant-direction maps can be overlaid with
quantum confidence maps for per-pixel directional analysis.
```

### 5.2 Quantum Branch A: QPIE Encoding + QHED (Yao et al., 2017)

**QPIE** encodes pixel intensity as a probability amplitude:
```
|psi> = (1/C) * SUM_{x,y} I(x,y) * |x>|y>

Intensity is in the AMPLITUDE, not in a computational basis register.
State preparation: RY rotations or isometry loading.
```

**QHED** applies Hadamard on the position register:
```
H|0> = (|0> + |1>) / sqrt(2)
H|1> = (|0> - |1>) / sqrt(2)

Adjacent pixels with amplitudes a and b:
  a = b  ->  amplitudes cancel  ->  P(edge) ~ 0
  a != b ->  amplitudes reinforce  ->  P(edge) proportional to |a-b|^2
```

Qubits (QPIE):
```
4x4:  ceil(log2(16)) + 1 ancilla = 5 qubits
8x8:  ceil(log2(64)) + 1 ancilla = 7 qubits
16x16: ceil(log2(256)) + 1 ancilla = 9 qubits
```

### 5.3 Quantum Branch B: NEQR Encoding + Quantum Gradient (Zhang et al., 2013)

**NEQR** stores exact binary intensity in the computational basis:
```
|Q> = (1/sqrt(N)) * SUM_{YX} |f(Y,X)>|YX>

|f(Y,X)> = |c7 c6 c5 c4 c3 c2 c1 c0>  (8-qubit binary intensity register)
|YX>      = position in computational basis

State preparation: multi-controlled CNOT gates per pixel.
NEQR does NOT use RY rotations or angle mappings.
```

**Quantum Gradient Operator** computes pixel differences via quantum arithmetic:
```
Horizontal difference at (x,y):
  |f(x,y)> - |f(x+1,y)>
  Implemented as a quantum subtractor on the intensity register.
```

Qubits (NEQR):
```
4x4:  4 pos + 8 int = 12 qubits (+ ancilla for arithmetic)
8x8:  6 pos + 8 int = 14 qubits
16x16: 8 pos + 8 int = 16 qubits

Qubit count grows LOGARITHMICALLY with image dimension.
Gate count, depth, and ancilla scale substantially -- measure separately.
```

### 5.4 Key Differences Between the Two Branches

| Property | QPIE + QHED | NEQR + Gradient |
|----------|-------------|-----------------|
| Intensity encoding | Probability amplitude | Computational basis (binary) |
| State preparation | RY / isometry | Multi-controlled CNOT |
| Edge operation | Hadamard interference | Quantum arithmetic subtractor |
| Logical qubits | Fewer | More |
| Exact pixel recovery | No (probabilistic) | Yes (deterministic in principle) |
| Canonical paper | Yao et al., 2017 | Zhang et al., 2013 + Wang et al., 2015 |

### 5.5 Measurement, Reconstruction, and Threshold Selection

```python
counts = aer_simulator.run(circuit, shots=8192).result().get_counts()

# Build continuous probability/strength map
for bitstring, count in counts.items():
    pos = parse_position(bitstring)
    edge_map[pos] = count / total_shots  # continuous, not binary
```

**Threshold selection (NOT fixed at T=0.1):**
```
1. Held-out validation subset (synthetic, known edges)
2. Sweep T over [0.01, 0.02, ..., 0.99]
3. Select T maximising boundary F1 on validation set
4. Freeze T, apply to test set
5. Report full PR curve (all thresholds)
```

### 5.6 Quantum Noise Simulation (AerSimulator)

```
AerSimulator (replaces deprecated qasm_simulator):
  |
  +-- Ideal mode
  |
  +-- Noisy mode:
        +-- Depolarizing noise: p in {0, 0.001, 0.005, 0.01, 0.05}
        +-- Readout error: bit-flip probability
        +-- Gate noise: over-rotation / coherent error
        +-- Combined: all above simultaneously
```

---

## 6. System Architecture

```
                        INPUT IMAGE
                             |
                             v
                   DATASET / IMAGE LOADER
                   (SomBench WAC | Synthetic | LRO)
                             |
                             v
                   PREPROCESSING MODULE
           +------------------+------------------+
           |                  |                  |
        Resize             Noise            Contrast
        Crop             Smoothing           CLAHE
        Normalise         Median             Gamma
           |                  |                  |
           +------------------+------------------+
                             |
           +-----------------+------------------+
           |                                    |
           v                                    v
 CLASSICAL PIPELINE                   QUANTUM PIPELINE
           |                                    |
  +-----+--+---+------+        +--------------+--------------+
  |     |       |      |       |                             |
Sobel Canny Robinson  |   QPIE + QHED              NEQR + Gradient
  |     |    (8-dir)  |   (Amplitude enc.)        (Basis-state enc.)
  |     |       |     |        |                             |
  +-----+-------+-----+   AerSimulator (ideal / noisy)      |
           |                    |              +--------------+
           |          Measurement (N shots, 10 trials)
           |                    |
           |         Reconstruction -> Confidence Map
           |                    |
           +----------+---------+
                      |
             GROUND TRUTH COMPARISON
           (Synthetic masks | SomBench COCO)
                      |
    +-----------+-----+-----------+----------+
    |           |                 |          |
    v           v                 v          v
Accuracy    Robustness       Resources   Failure
F1/P/R      Noise curves     Qubits      Analysis
IoU/Chamfer Blur curves      Depth
PR-AUC      Contrast curves  Gate count
Tol-F1      Q-noise curves   Kernel time
            Robustness AUC   E2E time
                      |
                      v
               RESEARCH CONCLUSIONS
```

---

## 7. Methodology

### Phase 1: Classical Baseline, Ground Truth, and Dataset Curation (Week 1)

```
1. Implement Sobel, Canny, and Robinson Compass using OpenCV / NumPy
2. Generate synthetic ground truth dataset:
   - Horizontal line, vertical line, 45-degree diagonal
   - Corner junction, circle, ellipse
   - Multiple circles, irregular curved boundary
   (Exact pixel-level masks available analytically)
3. Download full SomBench WAC crater detection benchmark (~1,000 images)
4. Browse and categorise images by:
   - Contrast level (low / medium / high)
   - Illumination angle (SomBench incidence angle metadata)
   - Crater rim size (small / medium / large)
   - Terrain complexity (flat / rough / overlapping)
5. Hand-pick 30 representative patches using stratified sampling
   (3 images per condition category, 10 categories = 30 patches)
6. Extract 8x8 and 16x16 patches from each selected image
7. Rasterise COCO polygon annotations to pixel-level binary GT masks
8. Apply Sobel, Canny, and Robinson to all patches and synthetic images
9. Evaluate classical methods against independent ground truth
10. Visualise: input | Sobel | Canny | Robinson | Ground truth
```

### Phase 2: QPIE + QHED Implementation (Week 2)

```
1. Study QPIE amplitude encoding and QHED (Yao et al., 2017)
2. Implement QPIE encoder: RY / isometry amplitude loading
3. Implement canonical QHED circuit: H + phase-kickback + H-dagger
4. Validate on synthetic 4x4 image (exact statevector check)
5. Threshold selection on validation subset (sweep T)
6. MNIST used only to confirm circuit runs (not scientific)
```

### Phase 3: NEQR + Quantum Gradient Implementation (Week 3)

```
1. Study NEQR encoding (Zhang et al., 2013)
2. Study quantum gradient operators (Wang et al., 2015)
3. Implement NEQR encoder with multi-controlled CNOT gates
4. Validate by measuring in computational basis (verify pixel values)
5. Implement quantum gradient / Sobel operator
6. Threshold selection on validation subset
7. Side-by-side: QPIE-QHED vs NEQR-Gradient vs Ground truth
```

### Phase 4-5: Systematic Experiments (Weeks 4-5)
See Section 8.

### Phase 6: Analysis and Writing (Week 6)

```
1. Compile all metric tables (mean +/- std, n=10 trials per config)
2. Plot robustness curves with AUC summaries
3. Build failure taxonomy with visual examples
4. Report kernel time and E2E time separately
5. Write final report; prepare presentation slides
6. Optional: Streamlit dashboard
```

---

## 8. Experimental Design

### Datasets and Sample Sizes

| Source | Total Available | Used | Ground Truth | Role |
|--------|----------------|------|-------------|------|
| SomBench WAC | ~1,000 (benchmark) | 30 (stratified) | COCO polygon rasterised masks | Main quantitative benchmark |
| Synthetic (generated) | 8-10 geometry types | All | Analytic pixel masks | Geometry ablation, circuit validation |
| NASA LRO | Unlimited (open) | 5-10 | None (visual only) | Qualitative external validation |
| MNIST | 70,000 | 5-10 | Not used for science | Circuit debugging only |

**SomBench curation:** 30 patches selected via stratified sampling across 10 condition categories (contrast × 3, illumination × 3, crater size × 2, terrain × 2). See Section 4 for full breakdown.

### Fixed Parameters

| Parameter | Value | Justification |
|-----------|-------|---------------|
| Bit depth | 8-bit (0-255) | Standard grayscale |
| Random seed | 42 | Reproducibility |
| Trials per configuration | 10 | Mean +/- std reporting |
| Simulator | Qiskit AerSimulator | Current recommended interface |
| Threshold | Validation-set selected | No arbitrary fixed value |

---

### Experiment 1 -- Representation Ablation (Core Experiment)

```
Control: Same image (8x8), same shots (8192), same preprocessing (none),
         same ideal simulator, same independent GT, same threshold

Variable: QPIE + QHED  vs  NEQR + Quantum Gradient

Measure (Edge Quality):
  Boundary F1 (exact, 1-px tol, 2-px tol), P, R, IoU, Chamfer, PR-AUC

Measure (Resources):
  Logical qubits, ancilla qubits, total qubits
  1q gates, 2q gates, circuit depth, state-prep gates
  Kernel time, end-to-end time

Dataset: Synthetic (exact GT) + SomBench patches
Trials: 10 per configuration, report mean +/- std
```

| Factor | QPIE-QHED | NEQR-Gradient |
|--------|-----------|---------------|
| Logical qubits | | |
| Ancilla qubits | | |
| Circuit depth | | |
| 2-qubit gates | | |
| Boundary F1 | | |
| Noise sensitivity | | |

---

### Experiment 2 -- Resolution Scaling

```
Variable: Image size (4x4, 8x8, 16x16)
Fixed: shots=8192, ideal simulator
Measure: Boundary F1, logical qubits, ancilla qubits,
         raw gate count, transpiled gate count, circuit depth,
         state-prep cost, kernel time, E2E time
Note: Qubit count grows logarithmically. Gate count and
      depth scale substantially. Measure ALL components separately.
Dataset: Synthetic circles (same geometry, varying resolution)
Trials: 10 per configuration
```

---

### Experiment 3 -- Measurement Shot Count

```
Variable: shots in {512, 1024, 2048, 4096, 8192, 16384, 32768}
Fixed: 8x8 image, ideal simulator, validation-selected threshold
Measure: Boundary F1 +/- std (n=10), PR-AUC, sampling variance
Dataset: Synthetic edges (exact GT)
Report: F1 vs shots with error bars
```

---

### Experiment 4 -- Image Noise and Degradation Robustness

4A -- Gaussian Noise:
```
Noise sigma: {0, 0.01, 0.03, 0.05, 0.10}
Measure: F1 for Sobel, Canny, QPIE-QHED, NEQR-Gradient
Report: Robustness AUC per method
```

4B -- Gaussian Blur:
```
Blur sigma: {0, 0.5, 1.0, 1.5, 2.0}
Measure: F1 for each method
```

4C -- Contrast Levels:
```
Contrast scale factor: {0.25, 0.50, 0.75, 1.00, 1.25}
Measure: F1 for each method
```

4D -- Illumination and Shadow (Lunar-Specific):
```
Conditions:
  Normal illumination
  Low illumination (intensity x0.3)
  Strong directional gradient (linear ramp)
  Shadow region (half-image darkened x0.7)
  SomBench real illumination (grouped by incidence angle metadata)
Measure: F1 per condition and method
```

---

### Experiment 5 -- Quantum Hardware Noise Simulation

```
Variable: AerSimulator noise model:
  - Ideal
  - Depolarizing: p in {0.001, 0.005, 0.01, 0.05}
  - Readout error: p in {0.01, 0.05, 0.10}
  - Gate noise (over-rotation)
  - Combined: all above

Fixed: 8x8 image, shots=8192
Methods: QPIE-QHED and NEQR-Gradient separately
Measure: F1, circuit fidelity, sampling variance
Trials: 10 per configuration
```

---

### Experiment 6 -- Synthetic Edge Geometry Ablation

Goal: Isolate effect of edge geometry with ALL other conditions fixed.

```
Variable: Synthetic geometry (IDENTICAL contrast, noise, resolution):
  Horizontal line | Vertical line | 45-degree diagonal
  Corner junction | Circle (r=4) | Ellipse (a=4, b=2)
  Multiple circles | Irregular curved boundary

Fixed: 8x8, same contrast, no noise, shots=8192, ideal simulator

Methods evaluated:
  Classical:  Sobel | Canny | Robinson Compass (8-direction)
  Quantum:    QPIE-QHED | NEQR-Gradient

Measure:
  Primary:    Boundary F1, Precision, Recall per geometry and method
  Robinson:   Dominant direction map (argmax_k |R_k|) per geometry
              Directional response strength per compass direction

Diagnostic use of Robinson in this experiment:
  For each geometry, Robinson identifies which compass direction
  responds most strongly. If QPIE-QHED or NEQR-Gradient F1 drops
  on a particular geometry:

  Case A: Robinson dominant direction is strong and clear
          -> Failure is QUANTUM-SPECIFIC (image is not inherently hard)
          -> Conclusion: quantum method has directional sensitivity

  Case B: Robinson also shows weak or inconsistent response
          -> Failure is IMAGE-LEVEL (low contrast, thin edges, etc.)
          -> Conclusion: all methods struggle, not quantum-specific

  This distinction is the core research value of including Robinson.

  Example analysis:
    Diagonal edge (45 degrees)
      Robinson 45-deg response: strong  -> image is well-defined
      QPIE-QHED F1: 0.61 (drops from 0.81 on horizontal)
      Conclusion: QPIE-QHED has measurable directional sensitivity

    Circular edge
      Robinson rotates through all 8 directions around the rim
      QPIE-QHED F1: 0.58 (drops further)
      Conclusion: circular geometry compounds directional limitation

Trials: 10 per geometry

NOTE: MNIST is NOT used here. MNIST and lunar images differ in
texture, contrast, noise, and structure -- confounding geometry comparisons.
Synthetic images change ONLY geometry; all else is identical.
```

---

### Experiment 7 -- Preprocessing Strategy

```
Variable: Preprocessing before quantum encoding:
  None | Gaussian (sigma=1) | Median (3x3)
  CLAHE (clip=2, tile=4x4) | Histogram stretch | Gamma (0.5 and 1.5)

Fixed: 8x8 SomBench patches, shots=8192, ideal simulator
Measure: Boundary F1 per method and strategy
```

---

### Experiment 8 -- Real Lunar Crater Benchmark (SomBench)

```
Dataset: 30 SomBench WAC crater patches (8x8 and 16x16)
GT: Rasterised COCO polygon rim annotations (independent)
Preprocessing: Best from Experiment 7, shots=8192, ideal

Methods: Sobel, Canny, QPIE-QHED, NEQR-Gradient

Measure:
  F1 (exact), F1 (1-px tol), F1 (2-px tol)
  Precision, Recall, IoU, Chamfer distance

Also: Group by SomBench incidence angle metadata
      Compare F1 across illumination groups

Trials: 10 per patch per method, report mean +/- std
```

---

### Experiment 9 -- Resource Scaling Analysis

```
Variable: Image size (4x4, 8x8, 16x16)
Methods: QPIE-QHED and NEQR-Gradient

Measure separately:
  Logical qubits | Ancilla qubits | Total qubits
  Raw gate count | Transpiled gate count
  1-qubit gate count | 2-qubit gate count
  Circuit depth (pre and post transpilation)
  State-preparation gate count
  Edge-operation gate count
  Peak memory (statevector bytes)
  Quantum KERNEL time (circuit.run() only)
  End-to-end time (prep + transpile + run + reconstruct)

Report kernel time AND E2E time SEPARATELY.
Do not claim quantum speed advantage from kernel time alone.
Classical Sobel/Canny E2E time reported for context.

Explicit statement:
  "This project evaluates edge detection quality and robustness,
   not quantum computational advantage. State preparation,
   measurement, and reconstruction dominate total quantum
   pipeline time at these small scales."
```

---

### Experiment 10 -- Failure Analysis

```
For each condition, show side-by-side:
  Input | GT | Sobel | Canny | QPIE-QHED | NEQR-Gradient

IMAGE-LEVEL FAILURE CONDITIONS:
  Low contrast (scale < 0.3)
  Heavy blur (sigma > 1.5)
  Strong noise (sigma > 0.05)
  Sparse/thin edge pixels
  Curved and diagonal boundaries
  Strong directional illumination gradient
  Shadow regions
  Low resolution (4x4)

QUANTUM-SPECIFIC FAILURE CONDITIONS:
  Insufficient shots (< 512)
  Depolarizing error > 1%
  Readout error > 5%
  Deep circuits (16x16 NEQR)
  Near-uniform regions (amplitude cancellation artefacts)

Per failure mode: identify which methods fail,
explain mechanism, assign severity (mild/moderate/severe)
```

---

## 9. Hypotheses

Pre-registered before running experiments:

| ID | Hypothesis |
|----|-----------|
| H1 | Increasing image degradation will reduce boundary F1 for all methods, but at different rates for QPIE-QHED and NEQR-Gradient |
| H2 | Increasing shot count will reduce statistical variance and improve F1, with diminishing returns above a saturation point |
| H3 | QPIE-QHED will show lower F1 on circular and diagonal edges than axis-aligned edges, due to directional Hadamard operation |
| H4 | Low-contrast crater rims will produce significantly lower quantum F1 than high-contrast rims |
| H5 | Quantum noise will degrade NEQR-Gradient more severely than QPIE-QHED at equal depolarizing rates, because NEQR circuits are deeper |
| H6 | Total resource cost will grow substantially with image resolution even though logical qubit count grows logarithmically |
| H7 | Preprocessing will improve quantum F1 on low-contrast SomBench patches but may reduce quality on already high-contrast synthetic edges |
| H8 | End-to-end quantum time will significantly exceed Sobel/Canny at all scales due to state preparation and measurement overhead |

---

## 10. Evaluation Metrics

### Primary Edge Quality Metrics

| Metric | Notes |
|--------|-------|
| Boundary F1 (exact) | Exact pixel match against independent GT |
| Boundary F1 (1-pixel tolerance) | GT dilated by 1px -- critical at 4x4 and 8x8 |
| Boundary F1 (2-pixel tolerance) | GT dilated by 2px |
| Precision | TP / (TP + FP) |
| Recall | TP / (TP + FN) |
| IoU | Jaccard index on edge pixels |
| Chamfer Distance | Mean nearest-edge-pixel distance |
| PR-AUC | Area under full precision-recall curve |

### Robustness Summary

```
Robustness AUC = Area under F1 vs degradation level curve
Higher AUC = method degrades more gracefully
Report per method, per degradation type
```

### Quantum Resource Metrics

| Metric | Measurement |
|--------|------------|
| Logical qubits | circuit.num_qubits |
| Ancilla qubits | from encoding sub-circuit |
| Circuit depth | circuit.depth() |
| Gate counts | circuit.count_ops() |
| Transpiled gate count | after transpile() |
| Kernel time | around aer_simulator.run() |
| End-to-end time | full pipeline wall-clock |

### Statistical Reporting (All results)

```
QPIE-QHED Boundary F1     = 0.XXX +/- 0.0XX  (n=10 trials, shots=8192)
NEQR-Gradient Boundary F1 = 0.XXX +/- 0.0XX
Sobel F1                   = 0.XXX +/- 0.000  (deterministic)
Canny F1                   = 0.XXX +/- 0.000
```

### Confidence / Uncertainty Maps

Quantum pipelines output continuous probability maps before thresholding:
```
Edge probability map (before threshold):
  0.02  0.04  0.09  0.73
  0.03  0.08  0.82  0.91

Enables: full PR curves, confidence visualisation,
         analysis of certainty vs shots/noise/contrast/blur
```

---

## 11. Project Timeline

```
Week 1: Classical Foundation and Ground Truth
  - Implement Sobel + Canny in OpenCV
  - Build synthetic ground truth dataset with analytic masks
  - Download SomBench WAC dataset; rasterise COCO annotations
  - Implement all evaluation metrics (F1, tolerance variants, PR-AUC)

Week 2: QPIE + QHED Implementation
  - Study QPIE amplitude encoding and QHED (Yao et al., 2017)
  - Implement QPIE encoder (RY / isometry)
  - Implement canonical QHED circuit (H + kickback + H-dagger)
  - Validate on synthetic 4x4 (statevector check)
  - Threshold selection via validation sweep

Week 3: NEQR + Quantum Gradient Implementation
  - Study NEQR encoding (Zhang et al., 2013)
  - Study quantum gradient operators (Wang et al., 2015)
  - Implement NEQR encoder (multi-controlled CNOT)
  - Validate by measuring computational basis
  - Implement quantum gradient operator
  - Threshold selection; side-by-side comparison with QHED

Week 4: Core Experiments
  - Experiment 1: Representation ablation (full resource breakdown)
  - Experiment 2: Resolution scaling
  - Experiment 3: Shot count (10 trials, error bars)
  - Experiment 6: Synthetic edge geometry ablation

Week 5: Robustness and Advanced Experiments
  - Experiment 4: Image noise (Gaussian, blur, contrast, illumination)
  - Experiment 5: Quantum hardware noise (AerSimulator noisy)
  - Experiment 7: Preprocessing strategies
  - Experiment 8: SomBench real lunar benchmark
  - Experiment 9: Detailed resource scaling

Week 6: Failure Analysis, Writing, Optional Dashboard
  - Experiment 10: Failure taxonomy (visual gallery)
  - Compile all tables (mean +/- std)
  - Plot robustness curves and AUC values
  - Write final report, prepare presentation slides
  - Optional: Streamlit research dashboard
```

---

## 12. Tech Stack and Dependencies

```
[quantum]
qiskit >= 1.0                Quantum circuit construction
qiskit-aer >= 0.14           AerSimulator (ideal + noisy)
qiskit-ibm-runtime           Optional: IBM Quantum cloud

[classical-vision]
opencv-python >= 4.9         Sobel, Canny, image I/O
scikit-image >= 0.22         Boundary metrics, edge comparison

[numerical]
numpy >= 1.26                Array operations
scipy >= 1.12                Gaussian noise, signal processing

[visualisation]
matplotlib >= 3.8            Plots, robustness curves, confidence maps
seaborn >= 0.13              Statistical plots, heatmaps

[data]
Pillow >= 10.0               Image I/O
pycocotools                  SomBench COCO annotation parsing
torchvision >= 0.17          MNIST (debugging only)

[results]
pandas >= 2.0                Results tables, CSV export
tqdm                         Progress bars

[optional]
streamlit >= 1.30            Interactive research dashboard

[dev]
jupyter                      Development notebooks
```

Installation:
```bash
pip install qiskit qiskit-aer qiskit-ibm-runtime
pip install opencv-python scikit-image numpy scipy
pip install matplotlib seaborn Pillow pycocotools
pip install pandas tqdm jupyter
pip install streamlit torchvision  # optional
```

---

## 13. Directory Structure

```
Quantum_Image/
|
+-- PROJECT_SUMMARY.md
|
+-- data/
|   +-- synthetic/
|   |   +-- generator.py             <- Create all geometry types
|   |   +-- images/                  <- Generated grayscale patches
|   |   +-- masks/                   <- Exact analytic ground truth masks
|   +-- sombench/
|   |   +-- images/                  <- 512x512 WAC grayscale tiles
|   |   +-- annotations/             <- COCO JSON annotations
|   |   +-- patches/                 <- Extracted 8x8 / 16x16 crater patches
|   |   +-- masks/                   <- Rasterised pixel-level rim masks
|   +-- nasa_lro/                    <- LRO tiles (qualitative validation only)
|   +-- mnist/                       <- MNIST (circuit debugging only)
|
+-- preprocessing/
|   +-- image_loader.py
|   +-- patch_extractor.py           <- Extract crater patches from SomBench
|   +-- annotation_rasteriser.py     <- COCO polygons -> pixel masks
|   +-- augmentor.py                 <- Noise, blur, contrast, illumination
|   +-- preprocessor.py             <- CLAHE, median, Gaussian, gamma
|
+-- classical/
|   +-- sobel.py
|   +-- canny.py
|   +-- robinson_compass.py          <- 8-direction Robinson compass operator
|   +-- classical_pipeline.py        <- Runs Sobel, Canny, and Robinson together
|
+-- quantum/
|   +-- qpie_encoder.py              <- QPIE amplitude encoding
|   +-- qhed_circuit.py              <- Canonical QHED circuit (Yao et al.)
|   +-- neqr_encoder.py              <- NEQR basis-state encoding (Zhang et al.)
|   +-- quantum_gradient.py          <- Quantum gradient / Sobel operator
|   +-- aer_runner.py                <- AerSimulator wrapper (ideal + noisy)
|   +-- noise_models.py              <- Depolarizing, readout, gate noise
|   +-- reconstruction.py            <- Edge map reconstruction from counts
|   +-- confidence_map.py            <- Continuous probability map output
|   +-- threshold_selector.py        <- Validation-set threshold sweep
|
+-- evaluation/
|   +-- metrics.py                   <- F1 (exact, 1px, 2px), P, R, IoU, Chamfer, PR-AUC
|   +-- robustness.py                <- Robustness curve + AUC
|   +-- resource_counter.py          <- Qubit, gate, depth, kernel/E2E timing
|   +-- visualiser.py                <- Plots, confidence maps, failure grids
|
+-- experiments/
|   +-- exp1_representation.py       <- QPIE-QHED vs NEQR-Gradient ablation
|   +-- exp2_resolution.py           <- Resolution scaling
|   +-- exp3_shots.py                <- Shot count + repeated trials
|   +-- exp4_image_noise.py          <- Gaussian, blur, contrast, illumination
|   +-- exp5_quantum_noise.py        <- AerSimulator noise models
|   +-- exp6_geometry.py             <- Synthetic edge geometry ablation
|   +-- exp7_preprocessing.py        <- Preprocessing strategies
|   +-- exp8_sombench.py             <- Real lunar crater benchmark
|   +-- exp9_resources.py            <- Resource scaling analysis
|   +-- exp10_failure_analysis.py    <- Failure taxonomy
|   +-- run_all.py                   <- Master script
|
+-- results/
|   +-- figures/
|   +-- tables/                      <- CSV (mean +/- std per config)
|   +-- circuits/                    <- Circuit diagrams
|   +-- confidence_maps/
|   +-- failure_gallery/             <- Failure taxonomy visual grids
|
+-- notebooks/
|   +-- 01_classical_baseline.ipynb
|   +-- 02_qpie_qhed.ipynb
|   +-- 03_neqr_gradient.ipynb
|   +-- 04_experiments.ipynb
|   +-- 05_results_analysis.ipynb
|
+-- dashboard/                       <- Optional Streamlit app
|   +-- app.py
|   +-- components/
|
+-- report/
    +-- final_report.pdf
    +-- presentation_slides.pptx
```

---

## 14. Optional Extensions

### Extension A: Streamlit Research Dashboard

```
User uploads a grayscale image, then selects:
  Resolution | Preprocessing | Quantum method | Shot count | Noise model

Output:
  Original | Sobel | Canny
  QPIE-QHED | NEQR-Gradient | Ground Truth (if provided)
  Quantum Confidence Map

Metrics panel:
  F1 | Precision | Recall | IoU | Chamfer
  Qubits | Depth | Gates | Kernel time | E2E time
```

### Extension B: IBM Quantum Hardware Proof-of-Concept

```
Scope: 4x4 synthetic image only (5 qubits QPIE / 12 qubits NEQR)
Platform: IBM Quantum free tier (Qiskit Runtime)
Purpose: Demonstrate circuit on real hardware as supplementary result
Constraints:
  - Hardware results are demonstration only, NOT primary science
  - Primary results remain simulator-based and fully reproducible
  - Hardware execution is NOT a project dependency
  - Document transpilation, qubit assignment, and reported error rates
```

---

## 15. References

1. Le, P.Q., Dong, F., & Hirota, K. (2011). A flexible representation of quantum images for polynomial preparation, image compression, and processing operations. *Quantum Information Processing*, 10(1), 63-84.

2. Zhang, Y., Lu, K., Gao, Y., & Wang, M. (2013). NEQR: A novel enhanced quantum representation of digital images. *Quantum Information Processing*, 12(8), 2833-2860.

3. Yao, X.W., Wang, H., Liao, Z., Chen, M., Pan, J., Li, J., ... & Zheng, D. (2017). Quantum image processing and its application to edge detection: Theory and experiment. *Physical Review X*, 7(3), 031041.

4. Wang, J., Jiang, N., & Wang, L. (2015). Quantum image translation. *Quantum Information Processing*, 14(5), 1589-1604.

5. Li, H., Song, S., & Fan, P. (2017). Quantum image edge detection based on eight-direction Sobel operator. *Quantum Information Processing*, 16(1), 1-15.

6. Canny, J. (1986). A computational approach to edge detection. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 8(6), 679-698.

7. Robinson, G.S. (1977). Edge detection by compass gradient masks. *Computer Graphics and Image Processing*, 6(5), 492-501. [Robinson Compass operator -- 8-direction classical baseline]

8. Silburt, A., Ali-Dib, M., Zhu, C., et al. (2019). Lunar crater identification via deep learning. *Icarus*, 317, 27-38.

9. NASA-IBM SomBench WAC Lunar Crater Detection Dataset. (2023). https://huggingface.co/datasets/ibm-nasa-geospatial/sombench

10. NASA Lunar Reconnaissance Orbiter Camera (LROC). (2024). LROC QuickMap. https://wms.lroc.asu.edu/lroc

11. IBM Quantum / Qiskit. (2024). Qiskit Documentation and AerSimulator Reference. https://docs.quantum.ibm.com

12. OpenCV Team. (2024). OpenCV Documentation. https://docs.opencv.org

---

*Last Updated: September 2026*
*Project Status: Planning Phase*
*Use Case: Lunar Crater Rim Edge Detection*
*Quantum Methods: QPIE+QHED (Branch A) | NEQR+Quantum Gradient (Branch B)*
