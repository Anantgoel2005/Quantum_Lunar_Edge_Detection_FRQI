# Quantum Lunar Edge Detection — FRQI

An independent FRQI live quantum edge-detection variant of [the original QPIE system](https://github.com/SamradhSahni/Quantum_Lunar_Edge_Detection), based on commit `32f49ddf9752a7152508e87f08200f59ec3eb199`. The original repository is unchanged. This repository preserves its Git history and attribution.

FRQI uses eight position qubits plus one brightness-angle qubit. For pixel i, theta_i = (pi/2) I_i/255; the state is a uniform superposition over positions with color state cos(theta_i)|0> + sin(theta_i)|1>. Position-register Hadamard interference produces the color-marginal probability p = (1 - cos(theta_a-theta_b))/N. The runner reconstructs absolute intensity differences as (1020/pi) arcsin(sqrt(N p/2)). Sampling estimates are clipped to the physical intensity range before reconstruction.

## Quantum Studio: individual-shot circuit visualizer

Open `visualization/circuit-studio/index.html` in a browser, or open it from the live detector. The offline simulator steps through every gate of an individual shot, showing complex amplitudes, probabilities, local Bloch vectors, measurement collapse, and shot counts. It includes Bell, GHZ, phase-interference, QPIE, and a 15-operation quantum-teleportation example with intermediate measurements and classical X/Z feed-forward. The studio is an ideal simulator for 1–6 qubits; it is separate from FRQI inference.

Run `node --test visualization/circuit-studio/test-simulator.cjs` to verify its state evolution and measurement branches. The teleportation preset transfers Alice's arbitrary complex state to Bob in every one of its four measurement branches; its final verification measurement is always zero.

## Run locally

Prerequisites: Git, **64-bit Python 3.12** (the tested version), and internet access for packages and the default dataset. Clone this repository and enter its directory first:

```powershell
git clone https://github.com/Anantgoel2005/Quantum_Lunar_Edge_Detection_FRQI.git
cd Quantum_Lunar_Edge_Detection_FRQI
```

Confirm `python --version` reports Python 3.12. No environment activation, quantum account, API key or GPU is required; inference uses the local ideal Aer simulator.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-real-case.txt
.\.venv\Scripts\python.exe data/sombench/fetch_case.py --row 0 --revision 20f800becb64a0c7ad314652a683f97f0281fe67
.\.venv\Scripts\python.exe visualization/build_real_case_view.py
.\.venv\Scripts\python.exe visualization/real_case_server.py
```

After setup, `./start_service.ps1` rebuilds the view and starts the service.

Keep the server terminal open; press **Ctrl+C** to stop it. If PowerShell blocks the launcher, use the explicit Python build/server commands above. If the port is occupied, stop the existing server or pass `--port 8771` to the server command. Each version needs its own virtual environment; QPIE uses port 8766, FRQI 8768 and NEQR 8769.

On macOS/Linux, use `python3.12 -m venv .venv` and replace `.\.venv\Scripts\python.exe` with `.venv/bin/python` in the commands. These platforms have not been validated here; compatible wheels for the pinned packages are required. Raw dataset TIFFs are excluded from Git and must be downloaded by the fetch command.

Open `http://127.0.0.1:8768/`. Run the entire native 512x512 lunar tile or upload a PNG, JPEG, WebP, BMP or TIFF. Preprocessing corrects orientation/transparency, fits uploaded images within 512 pixels per side, converts to grayscale, stretches global 2–98 percentile contrast and lightly denoises them. Upload limits are 20 MB and 16 million decoded pixels/samples. Regions are processed automatically using 16x16 blocks with one-pixel halos and four directional/pair-offset circuit passes per block.

The live view includes actual gate checkpoint playback, amplitude/measurement displays, a measured edge map, an overlay, and Sobel/Canny/Robinson comparisons on the identical working input. Catalog boundary metrics appear only for the labeled lunar case. Edge coverage on uploads is not accuracy.

## Execution and scientific limits

Execution is on the local ideal Qiskit Aer simulator, not quantum hardware. Aer-native Initialize prepares the exact FRQI state; the live display shows this as a preparation block. Exported QASM decomposes that preparation into primitive gates. We do not claim that arbitrary image loading is constant time or that this prototype provides a quantum speed advantage. Native Initialize is a simulation convenience, not free state preparation on hardware.

The actual detector is `quantum/variant_circuit.py`, called by `quantum/full_image.py`. Edge maps are reconstructed only from that circuit's measured counts. Classical work handles input preparation, probability calibration, halo stitching and final Otsu thresholding. Saved statevectors are used only for inspection/animation, never for the edge output. Playback shows actual checkpoints from the first inference block in each completed batch; it is slowed playback, not a hardware gate clock.

The FRQI lunar outputs go to `results/variants/frqi/row0/`. Historical QPIE outputs remain in `results/real_case/row0/` for attribution and reference; they are not served as FRQI outputs. Private uploads and verification fixtures remain excluded from Git. The original QPIE implementation is retained as `quantum/qpie_full_image.py` for regression tests and comparison. The inherited hybrid NEQR demonstration is a historical baseline, not this fork's live detector.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe visualization/verify_upload.py
```

52 tests pass, including exact encoded-state checks, both axes and pair offsets, constant-intensity cancellation, real measured halo stitching, and trace/count audit consistency. Browser upload validation uses installed Microsoft Edge and verifies actual inference, playback, measurement audit, all four comparison panels, invalid-file handling, and mobile layout. `tests/test_full_image.py` explicitly retains the original QPIE gradient-calibration tests; `tests/test_variant.py` verifies this variant's distinct operator.

## Matched encoding benchmark

These saved studies used historical four-bit NEQR. Multi-version drivers expect sibling folders named `Quantum_Lunar_Edge_Detection_QPIE`, `Quantum_Lunar_Edge_Detection_FRQI` and `Quantum_Lunar_Edge_Detection_NEQR`. Current eight-bit NEQR differs from the frozen sources; exact reproduction requires the archived four-bit version. This does not affect the live setup above.

Run `.\.venv\Scripts\python.exe experiments/run_encoding_matrix.py` to execute or resume
the QPIE/FRQI/NEQR benchmark. It uses eight fixed native 128x128 center crops from
distinct SomBench test products, excludes product IDs represented in the earlier
30-image selection, and compares three seeds at 1,024 and 8,192 shots per circuit.
All three methods receive identical pixels and disable block-minimum subtraction.
Sobel, Canny, Robinson, exact gradient, and exact quantized inequality are included.

Results and the frozen protocol are in `results/encoding_benchmark/`.
Run `experiments/verify_encoding_counts.py` to independently replay every saved
measurement audit, and `experiments/plot_encoding_benchmark.py` to export the figure.
Run `experiments/analyse_encoding_benchmark.py` last to append the metadata-based
geographic overlap sensitivity analysis and shot-budget comparisons to the report.
The original `experiments/benchmark_encodings.py` command is also supported, using
a new isolated interpreter per run; the persistent driver amortizes imports while
executing the identical randomized task order serially.

This is a crop-scale benchmark against approximate catalog rims. It does not establish
full-image crater-detection performance, geographical independence, or hardware speedup.

## BSDS500 development pilot

The BSDS pilot uses 20 fixed validation-only native crops with all human boundary
annotations. It compares QPIE, FRQI and NEQR, then tests smaller blocks at matched
total shot budgets and QPIE block-minimum subtraction on five preselected cases.
Test image and annotation downloads are explicitly rejected. To prepare and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-bsds.txt
.\.venv\Scripts\python.exe data/bsds500_setup.py
.\.venv\Scripts\python.exe experiments/run_bsds_parallel.py
.\.venv\Scripts\python.exe experiments/verify_bsds_summary.py
.\.venv\Scripts\python.exe experiments/bsds_outputs.py
```

Results are in `results/bsds_pilot/`. `experiments/bsds_pilot.py --verify-only`
independently replays all measured maps and recomputes boundary matching curves.
The evaluator uses validated SciPy one-to-one assignment and multi-annotator
matching with Guo-Hall thinning. Crop-scale development metrics and the 31-point
threshold grid are not official full-image BSDS500 scores. Boundary AP101 also
differs from the pixel average precision in the lunar benchmark.


## QPIE block-minimum subtraction follow-up

The separate `results/bsds_qpie_offset20/` experiment extends subtraction to all
20 pilot validation crops, adding 45 runs while retaining the original pilot.
It compares the remaining 15 images separately from the five that motivated
the experiment, using paired image-level F1 and gradient RMSE.

```powershell
.\.venv\Scripts\python.exe experiments/run_bsds_offset20.py
.\.venv\Scripts\python.exe experiments/analyse_bsds_offset20.py
```

The serial driver `experiments/bsds_offset20.py --verify-only` independently
replays all 120 paired records. Run the analysis command afterward to verify
summary arithmetic and regenerate the final interpretation. The report links
`validated_summary.json`, where improvement counts respect each metric's direction.

## Controlled output filtering

`results/bsds_filtering/` compares the saved QPIE baseline/subtraction maps and
the equally filtered exact-gradient magnitude at fixed Gaussian sigma 0, 0.5
and 1 pixel. Sobel/Robinson remain unchanged references. No new simulations are
required. Both filtered-target estimation error and original-target filter bias
are reported, together with paired image-level excess F1 gain over the exact control.

```powershell
.\.venv\Scripts\python.exe experiments/bsds_filtering.py
.\.venv\Scripts\python.exe experiments/verify_bsds_filtering.py
.\.venv\Scripts\python.exe experiments/bsds_filtering_outputs.py
```

This is a development-grid study on the existing validation crops; the whole
grid is reported and detector defaults remain unchanged.

## Provenance

Upstream: [SamradhSahni/Quantum_Lunar_Edge_Detection](https://github.com/SamradhSahni/Quantum_Lunar_Edge_Detection). Variant: [FRQI](https://github.com/Anantgoel2005/Quantum_Lunar_Edge_Detection_FRQI). SomBench dataset and Robbins crater catalog attribution are preserved in the run manifest and report; dataset license is CC BY 4.0. No new source-code license is introduced. See `README_QPIE_HISTORY.md` and inherited `report/` documents for the original analysis, limitations and results.


The live page links to expanded state preparation for the representative first image block. It displays actual U/CX/reset gates, exact rotation angles, paged circuit diagrams and full preparation QASM/JSON exports. A completed new input regenerates its own preparation export.
