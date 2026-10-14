# Quantum Lunar Edge Detection

A research prototype comparing QPIE/Hadamard edge detection, hybrid NEQR reconstruction, and classical detectors on tiny synthetic and lunar images.

## Automatic quantum detection on a real tile

The real-case pipeline processes the entire 512x512 image for SomBench metadata row 0, `M1290203799CE_r5872_c1112`. It executes 5,476 Qiskit QHED circuits with 44,859,392 shots and reconstructs edges from their measurement counts. Regions are handled automatically with overlapping 16x16 blocks. The inference path uses `quantum/full_image.py`; it does not use the analytical reference or NEQR's classical gradient.

The actual TIFF contains five float-valued bands. The default loader averages those bands and applies one global 2nd-to-98th percentile grayscale scaling. Each QPIE preparation subtracts its block minimum to improve measurement contrast without changing neighboring intensity differences. Known preparation norms calibrate probabilities before stitching; the final Otsu threshold is derived from the measured map without annotation-based tuning.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-real-case.txt
.\.venv\Scripts\python.exe data/sombench/fetch_case.py --row 0 --revision 20f800becb64a0c7ad314652a683f97f0281fe67
.\.venv\Scripts\python.exe experiments/real_case.py
.\.venv\Scripts\python.exe visualization/build_real_case_view.py
.\.venv\Scripts\python.exe visualization/real_case_server.py
```

Open `http://127.0.0.1:8766/`. The run button executes quantum detection on the complete fixed tile and displays live results from completed circuit batches. You can also upload an image; the entire working image is processed automatically without region selection. Measurement counts, input hashes, execution metadata, a primitive QASM example, comparison figures and a report are saved in `results/real_case/row0/`.

The live gate panel draws the actual eight-qubit circuits and animates preparation, controlled X/CX/CCX/MCX shifts, Hadamard interference, and measurement. Its amplitude grid is sourced from Aer `save_statevector` checkpoints on the first block of each completed batch; measurement frames use that circuit's actual counts. Block positions advance automatically. Pause or replay the latest block slowly without affecting detection. The animation is slowed checkpoint playback, not per-gate wall-clock telemetry. Initialize is shown as the native preparation block that Aer executes, while the decomposed primitive example remains available separately.

The `gate_trace.jsonl.gz` archive records all 86 traced blocks and 344 traced inference circuits for the default case. Twenty-eight correctness tests and a full browser run verify that checkpoints match the actual gate states, do not change measurement counts, and agree with the inference audit.

This is actual Qiskit circuit execution on a **local ideal Aer simulator**, not a quantum hardware run. Aer retains its supported image initialization instruction. Classical preparation/calibration/thresholding surround the quantum interference and measurement step. Classical edge detectors are separate comparison baselines. The catalog polygons are approximate rim references, and this single train-split case does not establish crater-object detection performance or quantum advantage.

Boundary F1 within one pixel was 0.251 for measured QHED and 0.315 for Sobel. The quantum edge map currently includes texture and illumination boundaries as well as crater rims. `quantum/tiled.py` remains an ideal analytical correctness reference; it is not used for the real-case output.

## Upload your own images

In the local detector at `http://127.0.0.1:8766/`, choose a file and click **Upload, preprocess & run live**. PNG, JPEG, WebP, BMP and TIFF are supported, with a 20 MB file limit and a 16-million-pixel limit (16 million samples for TIFF).

Preprocessing corrects EXIF orientation, composites transparency on white, fits the image within 512x512 pixels while preserving aspect ratio, converts to grayscale, normalizes global 2nd-to-98th percentile contrast, and applies a light Gaussian blur (sigma 0.8). Floating or multispectral TIFFs use the scientific loader. The original working-size preview and the actual preprocessed quantum input appear before inference starts.

The same Qiskit measurement pipeline then runs automatically, with live strengths, actual gate checkpoint animation and a magenta edge overlay. A four-panel comparison shows quantum QHED, Sobel, Canny and Robinson binary edge maps on that same preprocessed image. Edge counts, coverage percentages, threshold policies and downloadable PNGs are provided; coverage is not an accuracy score. Uploaded images have no catalog labels, so no accuracy scores are reported. Source files, preprocessing stages, measurement counts and reports stay in `results/user_images/<run-id>/`, excluded from Git. The active uploaded image remains selected while the local server is running; restarting the server restores the SomBench default.

Verify preprocessing and the browser workflow:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe visualization/verify_upload.py
```

## Corrected implementation

The October 2026 revision fixes measurement decoding, the vertical position qubit, missing neighboring pixel pairs, portable project paths, and floating-point evaluation scores. QHED now runs four circuits: horizontal and vertical, each with two pair offsets. A controlled modular increment covers boundaries missed by the unshifted Hadamard pass. Wraparound pairs are discarded, and edges are placed on the right/bottom pixel.

**NEQR-Gradient is hybrid:** quantum encoding and measurement reconstruct a four-bit image; a classical forward gradient extracts edges. It is not a coherent quantum gradient operator. `Forward-Gradient` and `Quantized-Gradient` provide matched classical controls.

## Validated results

Seeded validation uses three quantum trials, 8,192 shots per circuit, eight synthetic 8x8 images, and the supplied lunar patches. QHED spends four times the stated shots per trial. Classical scores use one deterministic evaluation.

| Method | Synthetic exact F1 | Lunar exact F1, pooled sizes |
| --- | ---: | ---: |
| Sobel | 0.8737 | 0.2845 |
| Robinson | 0.8663 | 0.2833 |
| Canny | 0.6862 | 0.0858 |
| Forward-Gradient | 0.6760 | 0.3145 |
| Quantized-Gradient | 0.6760 | 0.2436 |
| QPIE-QHED | 0.4522 | 0.1783 |
| NEQR-Gradient, hybrid | 0.6760 | 0.2436 |

Positive-mask lunar scores cover nine 8x8 and fifteen 16x16 patches. Thirty-four rim-free patch-size entries are evaluated separately for false positive pixels. Entries from the same source image are not independent. The low resolution, different operators and threshold policies prevent interpreting these scores as isolated representation effects or quantum advantage.

NEQR matches the classical quantized-gradient control in ideal simulation once positions are observed. The earlier scores remain in `results/tables/` as historical outputs; they were affected by implementation errors.

## Install and check

Python 3.12 was used for the tested core environment. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-core.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe experiments/validate_corrected.py --trials 3 --shots 8192
.\.venv\Scripts\python.exe experiments/generate_report.py
```

`requirements-core.txt` pins the top-level packages used for these checks. It is not a full transitive dependency lock. The original `requirements.txt` also includes optional dataset and plotting dependencies.

## Live circuit simulation

Open `visualization/index.html` in a browser; no server or network connection is needed. It uses a local ideal statevector simulator, checked against 12 Qiskit fixtures.

- Step through image preparation, controlled shift gates, Hadamard interference, and measurement.
- Run and pause playback; watch shots accumulate and edge estimates converge.
- Switch among four circuit passes and synthetic/lunar presets.
- Click pixels to edit the input and rerun.
- Inspect signed real amplitudes, the last measured basis state, sampled edges, and the exact combined edge map.

Preparation is shown as one block rather than animating all decomposed preparation gates. Individual measurement shots repeat preparation; this is an ideal classical simulation, not a hardware execution or noisy simulator stream.

Optional browser verification (uses installed Microsoft Edge):

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe visualization/verify_visualization.py
```

## Experiments and outputs

The original experiment entry points remain available:

```powershell
python experiments/run_all_experiments.py
python experiments/run_remaining_experiments.py
python experiments/run_exp7_exp10.py
python experiments/timing_analysis.py
python experiments/analysis.py
python experiments/generate_report.py
```

Use the installed environment's Python executable. New experiment tables and figures go to `results/corrected/`. Report generation summarizes available corrected CSVs without copying the old conclusions. The validation benchmark, primitive resource scaling and warmed-up timing have been rerun; the full ten-experiment suite has not.

Resource scaling decomposes preparation and operation gates into `u,cx`, reports each QHED pass separately, and includes NEQR measurement. These are primitive basis estimates, not device-specific routing or timing. Noisy runs also decompose to the gates covered by the configured channels. The `gate` noise mode remains a depolarizing approximation.

## Data and limitations

Included: 17 synthetic image/mask pairs and 58 lunar patches with masks. Raw lunar TIFFs and annotation JSON/parquet files are excluded. Regenerating patches requires the SomBench dataset and optional dependencies:

```powershell
python data/sombench/download_dataset.py
python experiments/phase1_pipeline.py
```

The curation pipeline now namespaces split image IDs and uses actual image dimensions for masks. The existing patches were not regenerated from absent raw annotations. Largest-crater-center sampling remains a limitation and can miss crater rims; benchmark scores do not establish crater detection performance on full lunar tiles.

PR area is recorded as average precision using floating scores. Trial standard deviations describe sampling variation, not a confidence interval over independent lunar images. Canny has only binary ranking scores. Simulation timings measure end-to-end local CPU calls, with one warmup excluded; separate kernel timing is not claimed.

See `report/fixes_and_validation.md`, `report/corrected_results_report.md`, and `report/repository_analysis.md` for details. The latter describes the original checkout. The repository retains its original academic-purpose statement; no new license is added by this revision.
