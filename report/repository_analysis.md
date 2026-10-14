# Repository analysis

Reviewed on 14 October 2026. Repository: [SamradhSahni/Quantum_Lunar_Edge_Detection](https://github.com/SamradhSahni/Quantum_Lunar_Edge_Detection).
Checked out `main` at `1bca9b3064543bbdad32a2a47c2613e1e9108e41` in `C:\Users\anant\Downloads\Quantum Lunar Detection`.

## Assessment

This is a useful research prototype with organized image preparation, classical baselines, two quantum encoding branches, evaluation metrics, ten experiment tables, and generated figures. Its current quantum comparisons are not reliable evidence about the relative merits of image representations: decoding and directional-operation defects materially change the images and edges being evaluated. Correct the implementation and rerun the experiments before using the scores in a paper or project defense.

The code and existing experiment outputs were inspected, followed by small simulator and statevector checks. The complete ten-experiment suite was not rerun. Original implementation files and existing result tables were left unchanged.

## What the project implements

- Classical branch: Sobel, Canny, and Robinson Compass in `classical/`.
- QPIE branch: intensity amplitudes prepared with `Initialize`, followed by a Hadamard on a selected position qubit; measurement counts become an edge map.
- NEQR branch: four-bit quantized intensities encoded with position-controlled X gates, measured back into a classical image, then differentiated with NumPy.
- Evaluation: exact and tolerant boundary F1, precision, recall, IoU, Chamfer distance, and PR-AUC against synthetic masks or rasterized crater annotations.
- Experiments: representation, shots, resolution, image degradation, circuit noise, geometry, preprocessing, lunar patches, resources, and failure categories.

Independent masks, geometry cases, and separate ideal/noisy experiments are good foundations. The basic NEQR state preparation passed an asymmetric image round-trip once its measurements were decoded correctly.

## Findings, ordered by impact

### 1. Measurement decoding corrupts positions and intensities

`quantum/qhed_circuit.py:118-127`, `quantum/neqr_encoder.py:159-167`, `quantum/quantum_gradient.py:75-81`, and `quantum/reconstruction.py:29` reverse measurement strings and then parse the reversed strings as ordinary binary numbers. Reversal is useful for indexing qubits, but parsing that representation without reversing it back changes its numeric value.

Qiskit count strings already put the most significant bit on the left; see [IBM's bit-ordering documentation](https://quantum.cloud.ibm.com/docs/en/guides/bit-ordering). For example, `001` means integer 1; the probability-map utility puts it at index 4.

Verified using a 4x4 image containing an asymmetric permutation of the 16 exactly representable four-bit levels, at 16,384 shots:

- Current NEQR verification reconstruction: mean absolute error **93.5 / 255**.
- Current NEQR gradient reconstruction: the same **93.5** error.
- Correct integer decoding of the same verification measurements: **0.0** error, with all 16 positions observed.
- QHED's horizontal reconstruction puts nonzero measurements at flat indices 0 through 7, whereas integer decoding places them at 0, 2, 4, ..., 14.

For NEQR, decode `value = int(bitstring, 2)`, `position = value >> intensity_bits`, and `intensity = value & ((1 << intensity_bits) - 1)`. For QHED, test the selected bit and clear it using integer masks. Apply the convention consistently across all reconstruction functions and verify it with asymmetric examples.

### 2. QHED's vertical direction operates along columns

`quantum/qhed_circuit.py:67` selects qubit 1 for every vertical run. With row-major 8x8 data, qubits 0, 1, and 2 encode columns; the least significant row bit is qubit **3**. For 4x4 and 16x16 images it is qubit 2 and 4 respectively.

An 8x8 row ramp, constant across columns, gave essentially zero vertical edge probability (about `2.6e-34`, numerical roundoff). The selected operation therefore fails to detect row variation. For power-of-two width, select `log2(width)` for the row bit and explicitly validate supported shapes.

### 3. QHED does not cover all neighboring pixel boundaries

A Hadamard on the least significant column bit compares disjoint pairs `(0,1)`, `(2,3)`, etc. Boundaries between these pairs require another pass with an appropriate shift/permutation. The implementation has no shifted pass.

Verified: an 8x8 image with columns 0-3 black and columns 4-7 white produced **zero nonzero pixels** in the combined sampled map at 16,384 shots. Its exact horizontal edge probability is only numerical roundoff. This failure exists independently of shot count. Consequently, attributing all complete misses to a measurement bottleneck is unsupported by the current implementation.

### 4. NEQR-Gradient uses a classical gradient

`quantum/quantum_gradient.py:97-114` computes adjacent differences with NumPy after measurement. No coherent quantum subtraction or quantum gradient operator is applied. The four-bit image is differentiated using forward differences, rather than the 3x3 Sobel kernel used by the classical baseline.

The experiment compares representation, quantization, reconstruction, gradient operator, and threshold policy simultaneously. It does not isolate representation choice. Describe this branch as NEQR reconstruction followed by a classical gradient, or implement the intended quantum operator. Add a classical four-bit quantization plus identical-gradient control to separate encoding effects from those other choices.

### 5. Resource counts hide state-preparation cost

`experiments/run_all_experiments.py:335-392` transpiles against Aer, which can retain `initialize` and multi-controlled instructions. Existing resource results report QHED depth 3 and zero CX gates, and also zero CX gates for NEQR. These are simulator instruction counts, not primitive hardware gate costs.

For one tested 8x8 QHED image, Aer retained depth **3** with one `initialize`; transpiling to the illustrative `u,cx` basis produced depth **118** and **57 CX gates**. This demonstrates hidden preparation cost; it is not a resource estimate for a specific device. Use a stated hardware target or primitive basis, include preparation, and verify that noise channels cover the gates that actually execute.

The "gate" noise mode is explicitly a depolarizing approximation, not a coherent over-rotation simulation.

### 6. The documented commands are not portable

Generators, loaders, and experiment scripts hard-code `E:\projects\Quantum_Image`. They can search the wrong directory or create output there. Installing requirements alone does not make the README commands work in this checkout.

Use `Path(__file__).resolve().parents[1]` for modules one directory below the root, and `parents[2]` for nested dataset scripts, or centralize configuration. The requirements specify minimum versions only; a tested lock or environment specification is needed for repeatable execution.

### 7. Benchmark and metric claims need qualification

The published headline exact-F1 means match the committed CSV aggregates:

| Method | Synthetic 8x8 | Lunar patches, pooled sizes |
| --- | ---: | ---: |
| Sobel | 0.8737 | 0.2845 |
| Robinson | 0.8663 | 0.2833 |
| Canny | 0.6862 | 0.0858 |
| NEQR-Gradient | 0.4641 | 0.2622 |
| QPIE-QHED | 0.0904 | 0.1602 |

These are existing results, not independently reproduced corrected scores. The lunar table contains 24 patch-size entries: nine 8x8 and fifteen 16x16, with five methods each. Its headline mean pools these sizes; it is not a result over all 29 selected images. The same source image can contribute at both sizes, so these entries are not necessarily independent.

Empty-mask patches are excluded, so the benchmark does not measure false positives on rim-free patches. Centering tiny patches on the largest crater can omit its rim; patch sampling should include rim locations and independently sampled negatives. Raw TIFFs and annotation files are absent, although 58 patches and 58 masks are included.

Further limitations:

- QHED continuous probabilities are multiplied by 255 and cast to uint8 before PR-AUC; probabilities below `1/255` become zero. Keep floating scores for ranking metrics.
- Canny is evaluated with binary scores for PR-AUC, giving much less ranking information than continuous detector strengths.
- The reconstruction helper's `otsu` mode uses the mean of positive values, rather than Otsu thresholding.
- NumPy's random seed does not seed Aer sampling or transpilation; record explicit simulator/transpiler seeds and environment versions.
- Test and validation annotations are merged by `image_id` without the ID offset promised in a comment. If split IDs overlap, annotations can be mixed. This risk could not be checked against the omitted raw JSON files.
- Resolution scaling uses one 4x4 geometry versus three 8x8 geometries, so its means confound size with geometry.
- Timing code measures total calls only, despite promising separate kernel timing, and uses five runs without explicit warmup. The stated slowdown ratios describe these local CPU simulations.
- No automated test suite, dependency lock, or conventional license file was found. The README's academic-purpose statement does not establish general reuse permissions.

## Validation and next steps

Diagnostics are in `analysis_checks.py`; outputs are in `analysis_checks.json`. Run from the repository root:

```powershell
.\.venv\Scripts\python.exe report/analysis_checks.py
```

A local `.venv` was created with access to existing system packages, and Qiskit Aer 0.17.2 was installed into it. Checks used Python 3.12.10, Qiskit 2.5.1, and NumPy 2.5.1. All 30 original Python source files parsed successfully. Classical pipeline output shapes, NEQR encoding/decoding, QHED directional behavior, pair coverage, primitive decomposition, CSV aggregation, and included-data counts were checked. Simulator sampling remains unseeded because the original entry points do not expose a seed; the reported structural failures are corroborated by exact statevector checks or complete position coverage.

First fix decoding, direction selection, and neighboring-boundary coverage. Then clarify or implement the NEQR gradient, add matched classical controls, remove hard-coded roots, preserve floating scores, and introduce meaningful correctness tests. Finally rerun the benchmark with controlled seeds, primitive resource accounting, rim-positive and negative patches, and uncertainty aggregated across independent source images. Existing quantum tables should be treated as historical prototype outputs until that rerun is complete.
