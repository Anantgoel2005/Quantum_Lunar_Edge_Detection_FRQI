# Quantum Lunar Edge Detection — FRQI

An independent FRQI live quantum edge-detection variant of [the original QPIE system](https://github.com/SamradhSahni/Quantum_Lunar_Edge_Detection), based on commit `32f49ddf9752a7152508e87f08200f59ec3eb199`. The original repository is unchanged. This repository preserves its Git history and attribution.

FRQI uses eight position qubits plus one brightness-angle qubit. For pixel i, theta_i = (pi/2) I_i/255; the state is a uniform superposition over positions with color state cos(theta_i)|0> + sin(theta_i)|1>. Position-register Hadamard interference produces the color-marginal probability p = (1 - cos(theta_a-theta_b))/N. The runner reconstructs absolute intensity differences as (1020/pi) arcsin(sqrt(N p/2)). Sampling estimates are clipped to the physical intensity range before reconstruction.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-real-case.txt
.\.venv\Scripts\python.exe data/sombench/fetch_case.py --row 0 --revision 20f800becb64a0c7ad314652a683f97f0281fe67
.\.venv\Scripts\python.exe visualization/build_real_case_view.py
.\.venv\Scripts\python.exe visualization/real_case_server.py
```

After setup, `./start_service.ps1` rebuilds the view and starts the service.

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

32 tests pass, including exact encoded-state checks, both axes and pair offsets, constant-intensity cancellation, real measured halo stitching, and trace/count audit consistency. Browser upload validation uses installed Microsoft Edge and verifies actual inference, playback, measurement audit, all four comparison panels, invalid-file handling, and mobile layout. `tests/test_full_image.py` explicitly retains the original QPIE gradient-calibration tests; `tests/test_variant.py` verifies this variant's distinct operator.

## Provenance

Upstream: [SamradhSahni/Quantum_Lunar_Edge_Detection](https://github.com/SamradhSahni/Quantum_Lunar_Edge_Detection). Variant: [FRQI](https://github.com/Anantgoel2005/Quantum_Lunar_Edge_Detection_FRQI). SomBench dataset and Robbins crater catalog attribution are preserved in the run manifest and report; dataset license is CC BY 4.0. No new source-code license is introduced. See `README_QPIE_HISTORY.md` and inherited `report/` documents for the original analysis, limitations and results.
