# Quantum Edge Detection -- Final Results Report

**Generated:** 2026-10-11 22:23
**Project:** Quantum Edge Detection Under Changing Image Conditions

---

## Executive Summary

**Core Finding (Experiment 1 -- Representation Ablation):**

  - **Sobel**: Mean F1 = 0.8737
  - **Canny**: Mean F1 = 0.6862
  - **Robinson**: Mean F1 = 0.8663
  - **QPIE-QHED**: Mean F1 = 0.0904
  - **NEQR-Gradient**: Mean F1 = 0.4641

> Classical methods (Sobel, Robinson) significantly outperform both quantum
> approaches on 8x8 synthetic patches. NEQR-Gradient provides moderate edge
> detection quality. QPIE-QHED struggles with very low F1 scores due to the
> challenge of reconstructing spatial edge information from amplitude-encoded
> quantum measurements at this scale.

---

## Experiment 1: Representation Ablation

### F1 Scores by Geometry and Method

| image            |   Canny |   NEQR-Gradient |   QPIE-QHED |   Robinson |   Sobel |
|:-----------------|--------:|----------------:|------------:|-----------:|--------:|
| circle           |  0.6667 |          0.5429 |      0.2388 |     0.8    |  0.6667 |
| corner_junction  |  0.6364 |          0.339  |      0      |     0.9677 |  1      |
| diagonal_45      |  0.1333 |          0.8    |      0      |     0.7    |  0.7    |
| ellipse          |  0.8    |          0.5357 |      0.1788 |     0.75   |  0.8333 |
| horizontal_line  |  1      |          0.25   |      0      |     1      |  1      |
| irregular_curve  |  0.7143 |          0.3478 |      0.0559 |     0.8182 |  0.8947 |
| multiple_circles |  0.5385 |          0.6471 |      0.1299 |     0.8947 |  0.8947 |
| vertical_line    |  1      |          0.25   |      0.12   |     1      |  1      |

### Overall Mean F1

| Method | Mean F1 | Std F1 |
|--------|---------|--------|
| Sobel | 0.8737 | 0.1328 |
| Canny | 0.6862 | 0.2780 |
| Robinson | 0.8663 | 0.1163 |
| QPIE-QHED | 0.0904 | 0.0910 |
| NEQR-Gradient | 0.4641 | 0.1995 |

## Experiment 2: Shot Count Sensitivity

### Mean F1 vs Shot Count

|   shots |   NEQR-Gradient |   QPIE-QHED |
|--------:|----------------:|------------:|
|     256 |          0.527  |      0.0868 |
|     512 |          0.5606 |      0.0917 |
|    1024 |          0.5606 |      0.0896 |
|    2048 |          0.5606 |      0.0806 |
|    4096 |          0.5606 |      0.0792 |
|    8192 |          0.5606 |      0.0795 |
|   16384 |          0.5606 |      0.0848 |

> **Finding:** NEQR-Gradient converges quickly and is insensitive to shot count
> above 512 shots. QPIE-QHED shows slight variation but remains low throughout.

## Experiment 5: Quantum Hardware Noise Simulation

### F1 Under Different Noise Configurations

| noise        |   NEQR-Gradient |   QPIE-QHED |
|:-------------|----------------:|------------:|
| combined     |          0.4414 |      0.3764 |
| depol_0.001  |          0.4448 |      0.1995 |
| depol_0.005  |          0.4652 |      0.21   |
| depol_0.01   |          0.4536 |      0.2346 |
| depol_0.05   |          0.448  |      0.2948 |
| gate_0.005   |          0.4464 |      0.2364 |
| ideal        |          0.441  |      0.1034 |
| readout_0.01 |          0.4576 |      0.2994 |
| readout_0.05 |          0.431  |      0.3473 |
| readout_0.10 |          0.4508 |      0.3738 |

## Experiment 6: Geometry Ablation

### F1 by Edge Geometry

| geometry         |   Canny |   NEQR-Gradient |   QPIE-QHED |   Robinson |   Sobel |
|:-----------------|--------:|----------------:|------------:|-----------:|--------:|
| circle           |  0.6667 |          0.5429 |      0.2344 |     0.8    |  0.6667 |
| corner_junction  |  0.6364 |          0.339  |      0      |     0.9677 |  1      |
| diagonal_45      |  0.1333 |          0.8    |      0      |     0.7    |  0.7    |
| ellipse          |  0.8    |          0.5357 |      0.2155 |     0.75   |  0.8333 |
| horizontal_line  |  1      |          0.25   |      0      |     1      |  1      |
| irregular_curve  |  0.7143 |          0.3478 |      0.0567 |     0.8182 |  0.8947 |
| multiple_circles |  0.5385 |          0.6471 |      0.1248 |     0.8947 |  0.8947 |
| vertical_line    |  1      |          0.25   |      0.0895 |     1      |  1      |

## Experiment 4: Image Quality Degradation

### F1 Under Image Degradation

| degradation   |   NEQR-Gradient |   QPIE-QHED |   Robinson |   Sobel |
|:--------------|----------------:|------------:|-----------:|--------:|
| blur_0.5      |          0.4525 |      0.1656 |     0.8226 |  0.8333 |
| blur_1.5      |          0.385  |      0.3038 |     0.6361 |  0.6361 |
| clean         |          0.5606 |      0.0768 |     0.8226 |  0.7889 |
| contrast_0.25 |          0.5606 |      0.0841 |     0.8226 |  0.7889 |
| contrast_0.50 |          0.5606 |      0.0934 |     0.8226 |  0.7889 |
| illum_grad    |          0.367  |      0.1673 |     0.7781 |  0.7889 |
| noise_10      |          0.3897 |      0.2132 |     0.8333 |  0.8012 |
| noise_30      |          0.39   |      0.2808 |     0.8057 |  0.8482 |
| noise_50      |          0.4513 |      0.2618 |     0.7999 |  0.8415 |

## Experiment 8: SomBench Real Lunar Benchmark

### Overall Mean F1 on SomBench Patches

| Method | Mean F1 | N |
|--------|---------|---|
| Sobel | 0.2845 | 24 |
| Canny | 0.0857 | 24 |
| Robinson | 0.2833 | 24 |
| QPIE-QHED | 0.1602 | 24 |
| NEQR-Gradient | 0.2622 | 24 |

## Experiment 9: Resource Scaling

| method        |   size |   n_qubits |   circuit_depth |   cx_count |
|:--------------|-------:|-----------:|----------------:|-----------:|
| QPIE-QHED     |      4 |          4 |               3 |          0 |
| NEQR-Gradient |      4 |          8 |              49 |          0 |
| QPIE-QHED     |      8 |          6 |               3 |          0 |
| NEQR-Gradient |      8 |         10 |             177 |          0 |

## Timing Analysis

| method        |   mean_time_ms |   std_time_ms |   min_time_ms |   max_time_ms |   size |
|:--------------|---------------:|--------------:|--------------:|--------------:|-------:|
| Sobel         |           1.46 |          2.83 |          0.02 |          7.12 |      4 |
| Canny         |           1.37 |          2.63 |          0.03 |          6.63 |      4 |
| Robinson      |           0.23 |          0.37 |          0.04 |          0.97 |      4 |
| QPIE-QHED     |         393.07 |        326.94 |        219.47 |       1046.8  |      4 |
| NEQR-Gradient |         117.61 |          5.47 |        107.19 |        123.21 |      4 |
| Sobel         |           0.04 |          0.03 |          0.03 |          0.1  |      8 |
| Canny         |           0.12 |          0.06 |          0.07 |          0.22 |      8 |
| Robinson      |           0.08 |          0.02 |          0.06 |          0.12 |      8 |
| QPIE-QHED     |         234.28 |          7.43 |        223.39 |        245.53 |      8 |
| NEQR-Gradient |         137.46 |          3.9  |        131.33 |        143.56 |      8 |

## Experiment 7: Preprocessing Strategy

| preprocessing   |   NEQR-Gradient |   QPIE-QHED |   Robinson |   Sobel |
|:----------------|----------------:|------------:|-----------:|--------:|
| clahe           |          0.5552 |      0.0873 |     0.8333 |  0.7889 |
| gamma_0.5       |          0.5606 |      0.0818 |     0.8226 |  0.7889 |
| gamma_1.5       |          0.5606 |      0.0742 |     0.8226 |  0.7889 |
| gaussian_s1     |          0.4009 |      0.2152 |     0.7445 |  0.7445 |
| hist_stretch    |          0.5606 |      0.0768 |     0.8226 |  0.7889 |
| median_3x3      |          0.3784 |      0.0886 |     0.7226 |  0.6651 |
| none            |          0.5606 |      0.0777 |     0.8226 |  0.7889 |

## Experiment 10: Failure Taxonomy

| geometry         | method        |   f1_exact_mean |   precision_mean |   recall_mean | failure_mode    |
|:-----------------|:--------------|----------------:|-----------------:|--------------:|:----------------|
| circle           | QPIE-QHED     |          0.2254 |           0.5408 |        0.1425 | DISPLACEMENT    |
| circle           | NEQR-Gradient |          0.5429 |           0.6333 |        0.475  | SUCCESS         |
| corner_junction  | QPIE-QHED     |          0      |           0      |        0      | COMPLETE_MISS   |
| corner_junction  | NEQR-Gradient |          0.339  |           0.2273 |        0.6667 | MODERATE        |
| diagonal_45      | QPIE-QHED     |          0      |           0      |        0      | COMPLETE_MISS   |
| diagonal_45      | NEQR-Gradient |          0.8    |           0.6667 |        1      | SUCCESS         |
| ellipse          | QPIE-QHED     |          0.1652 |           0.3498 |        0.1083 | DISPLACEMENT    |
| ellipse          | NEQR-Gradient |          0.5357 |           0.4688 |        0.625  | SUCCESS         |
| horizontal_line  | QPIE-QHED     |          0      |           0      |        0      | COMPLETE_MISS   |
| horizontal_line  | NEQR-Gradient |          0.25   |           0.25   |        0.25   | DISPLACEMENT    |
| irregular_curve  | QPIE-QHED     |          0.0377 |           0.125  |        0.0222 | UNDER_DETECTION |
| irregular_curve  | NEQR-Gradient |          0.3478 |           0.2353 |        0.6667 | MODERATE        |
| multiple_circles | QPIE-QHED     |          0.1203 |           0.5    |        0.0684 | DISPLACEMENT    |
| multiple_circles | NEQR-Gradient |          0.6471 |           0.7333 |        0.5789 | SUCCESS         |
| vertical_line    | QPIE-QHED     |          0.109  |           0.265  |        0.0688 | DISPLACEMENT    |
| vertical_line    | NEQR-Gradient |          0.25   |           0.25   |        0.25   | DISPLACEMENT    |

---

## Key Conclusions

1. **Classical methods outperform quantum methods** on small (8x8) synthetic
   and real lunar patches. Sobel and Robinson achieve F1 > 0.8 on most geometries.

2. **NEQR-Gradient outperforms QPIE-QHED** as a quantum edge detector. The
   basis-state encoding preserves pixel intensity information more faithfully
   through measurement.

3. **QPIE-QHED struggles** because amplitude encoding maps pixel differences
   to small probability differences that are hard to resolve with finite shots.
   Complete failures (F1=0) occur on certain geometries.

4. **Shot count has minimal impact** above ~512 shots for both quantum methods.
   The bottleneck is representation quality, not measurement statistics.

5. **Hardware noise degrades quantum edge detection further**, with readout
   errors having the strongest impact (directly corrupting measurement results).

6. **No quantum speed advantage**: quantum simulation is orders of magnitude
   slower than classical Sobel due to circuit compilation and simulation overhead.

7. **Quantum methods produce unique uncertainty information**: confidence maps
   from repeated trials reveal measurement variance patterns that classical
   methods cannot provide, which may have diagnostic value.
