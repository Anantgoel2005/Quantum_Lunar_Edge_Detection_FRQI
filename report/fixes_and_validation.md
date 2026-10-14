# Fixes and validation

Applied to the local checkout on 14 October 2026, based on commit `1bca9b3`. Changes are uncommitted.

## Implemented

- Correct integer decoding for QHED probability maps and NEQR position/intensity registers; remove unused measurement-register construction.
- Correct vertical position-bit selection for square and rectangular power-of-two images.
- Add controlled modular shifts and two pair offsets in each direction, covering all neighboring pixels. Discard circular boundary pairs and place edges at right/bottom endpoints.
- Share finite-difference processing between NEQR reconstruction and matched classical controls; explicitly document NEQR as a hybrid pipeline.
- Preserve floating scores for evaluation, implement true interclass-variance thresholding, support binary 0/1 masks, and use average precision for PR area so constant predictors receive the prevalence baseline.
- Validate shapes, nonfinite/negative inputs, intensity bit depths and shot counts; expose reproducible simulator and transpiler seeds. Experiment trials use different deterministic seeds.
- Decompose noisy execution into the `u,cx` gates covered by noise models; resource scaling reports each QHED circuit and its primitive preparation cost.
- Replace machine-specific paths across generators, loaders, examples and experiments. Namespace split image IDs during annotation merging and use image dimensions for rim masks.
- Store corrected tables and figures separately, generate reports from available data, and remove fixed conclusions from the report generator.
- Exclude warmup from timing; describe timings as total local CPU costs. Correct failure classification so a prediction with no overlap is not automatically called an empty prediction.
- Add an interactive circuit simulator and pinned core dependency specification.

## Correctness checks

Eleven tests in `tests/test_quantum.py` cover asymmetric NEQR reconstruction, the matched control, count ordering, exact horizontal and vertical gradients on four square/rectangular shapes, all neighbor boundaries, uniform inputs, seeded repeatability, invalid input, thresholding, binary-mask/constant-score metrics and noisy execution.

The exact expected QHED directional value is `(I_neighbor - I_pixel)^2 / (2 * sum(I^2))`. Both pair offsets reproduce it, including boundaries omitted by the original implementation. A split 8x8 image now yields exactly eight edge locations at column 4; the original combined implementation yielded none.

The asymmetric NEQR check reconstructs all 16 representable levels with zero error. Its ideal hybrid edge output matches the classical quantized forward-gradient control to floating-point precision.

## Seeded benchmark

The validation benchmark reruns eight synthetic 8x8 images and all 58 supplied lunar patch-size entries. Each quantum method uses three trials with 8,192 shots per circuit. QHED runs four circuits per trial; NEQR runs one. There are 32 positive-mask entries (8 synthetic, 24 lunar) and 34 rim-free lunar entries, each evaluated with seven methods.

| Method | Original synthetic F1 | Corrected synthetic F1 | Corrected positive lunar F1 |
| --- | ---: | ---: | ---: |
| Sobel | 0.8737 | 0.8737 | 0.2845 |
| Robinson | 0.8663 | 0.8663 | 0.2833 |
| Canny | 0.6862 | 0.6862 | 0.0858 |
| QPIE-QHED | 0.0904 | 0.4522 | 0.1783 |
| NEQR-Gradient, hybrid | 0.4641 | 0.6760 | 0.2436 |
| Forward-Gradient | — | 0.6760 | 0.3145 |
| Quantized-Gradient | — | 0.6760 | 0.2436 |

Original and corrected quantum runs differ in implementation and QHED shot budget, so this table is a diagnostic comparison rather than a controlled effect estimate. Classical scores remain unchanged. The equality between NEQR and the quantized control demonstrates that its ideal edge behavior is explained by classical quantization and differentiation after reconstruction.

Detailed per-image F1, average precision and trial variation are in `results/corrected/tables/validation_benchmark.csv`; negative-patch false positive counts are separate. Versions, seeds and shot budgets are recorded in `results/corrected/validation_metadata.json`.

Primitive resource scaling and warmed-up timing were also rerun. On the resource test's 8x8 image, QHED uses six position qubits and 57 or 62 CX gates per pass; NEQR uses ten qubits and 6,021 CX gates for preparation/measurement. These are `u,cx` basis counts, not routed device costs or proof of hardware advantage. Local simulation remains much slower than classical operations.

## Live circuit view

Open `visualization/index.html`. It runs an ideal real-amplitude statevector calculation locally, with controlled X gates, Hadamard interference and Born-probability sampling. You can pause, step through gates, edit pixels, switch presets/passes and change playback speed or shot budget. The exact combined edge map updates immediately; the selected pass's sampled map accumulates during playback.

`visualization/verify_visualization.py` compared twelve fixtures against Qiskit. Maximum amplitude error was `5.6e-17`; maximum edge-probability error was `8.7e-18`. Playback completed its shot budget and controls worked without JavaScript errors or horizontal overflow at 360px. Desktop/mobile previews and machine-readable verification results are included.

Image initialization is displayed as a single preparation block; the primitive gates for that block are not animated. Each shot represents a fresh preparation and measurement. The browser simulation is not connected to a QPU or a live Aer process and does not simulate noise. The Python pipeline remains the benchmark/noise implementation.

## Remaining scientific limitations

The full ten-experiment suite has not been rerun. Original tables, figures and the final historical report remain untouched. Raw TIFFs and annotations are absent, so patches were not regenerated and the ID-merging correction could not be checked against the original dataset files. Largest-crater-center sampling can omit rims; full-image crater detection and independent-image uncertainty estimates remain unvalidated.

NEQR does not implement a coherent quantum gradient. Its four-bit quantization, classical forward-difference operator, and threshold policy differ from Sobel/Canny. Resource estimates do not include a specific device's topology. The `gate` noise mode remains a depolarizing approximation. The pinned core requirements are not a complete transitive lock; plotting and dataset preparation require the optional dependencies in the original requirements file.
