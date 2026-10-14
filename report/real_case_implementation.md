# Automatic quantum edge detection on SomBench row 0

The complete tile `M1290203799CE_r5872_c1112` is processed automatically. The image is taken from the exact dataset revision `20f800becb64a0c7ad314652a683f97f0281fe67`; metadata row 0 belongs to the annotation train split and has 122 crater annotations. Its TIFF actually has shape `(512,512,5)`, axes `YXS`, and float32 samples.

## Inference path

1. Load all five bands, average them, and apply one global percentile scaling to grayscale. Record the original shape, band policy, scaling values, and input hashes.
2. Cover the complete image with 1,369 automatically positioned 16x16 blocks. Each block contributes a 14x14 core and uses its one-pixel halo for neighboring differences. Partial cores at image borders are cropped to the original coordinates.
3. Subtract each block minimum and normalize it into QPIE amplitudes. This changes the preparation norm and measurement efficiency, while preserving the neighboring intensity differences being estimated.
4. Build four circuits per block: horizontal/vertical, unshifted/shifted pairs. Execute preparation, controlled shifts, Hadamard interference and measurement with Qiskit Aer. Each circuit receives 8,192 shots.
5. Obtain edge probabilities from actual circuit `get_counts()` results. Calibrate them with the known preparation norm, stitch the core estimates, normalize the full-image magnitude and apply Otsu thresholding.
6. Build the annotation reference only after inference and compute comparison metrics. Sobel, Canny and Robinson are separate baselines and do not supply the quantum output.

The analytical shortcut and the hybrid NEQR gradient are not called by this inference path. In total the run executed **5,476 circuits and 44,859,392 measurement shots**. Every circuit's counts, preparation norm, offset, coordinates, seed and job ID are saved in a compressed JSON-lines audit. A representative circuit is also exported after decomposition to primitive `u,cx` gates.

Execution is a local ideal statevector quantum-circuit simulation, not a QPU run. Aer executes QPIE preparation using its supported Initialize instruction, followed by the explicit controlled and Hadamard gates. This does not demonstrate efficient state preparation on hardware or a quantum speed advantage.

## Automatic view

Run `visualization/real_case_server.py` and open `http://127.0.0.1:8766/`. The view shows the complete input and quantum output. Its single run action launches `experiments/real_case.py` on the fixed tile. Progress, measured shot totals and the growing strength map come from the backend's actual completed circuit batches. There is no image upload, crop control or manual patch-selection mechanism.

The original synthetic circuit explainer remains available separately. It is not the real-data inference interface.

### Live gate checkpoints

The real detector now instruments the first automatically processed block of each batch, saving its actual statevector after image preparation and every controlled/one-qubit gate. The visualizer draws the gates directly from those Qiskit circuits, highlights each checkpoint, shows its signed real amplitudes, and switches to observed probabilities for measurement. The four directional/pair-offset passes are animated automatically, with the traced block outlined on the full image. The block is chosen by the backend, not by a region-selection interface.

The default full run produces 86 checkpoint packets covering 344 inference circuits. Every measurement histogram in the trace has the same job ID and counts as its entry in the edge-detection audit. Pause and slow replay control only the animation; the detector continues independently.

Aer delivers checkpoints after a batch finishes and does not expose per-gate wall-clock callbacks. The animation therefore plays exact saved states arriving during the live run; its visual timing is intentionally slower than gate execution. It does not claim to display a hardware clock or animate decomposed preparation gates that the ideal backend retains as Initialize. State saves are placed before final measurement so terminal-measurement sampling stays enabled.

## Validation

Twenty-two tests pass across the original circuits, analytical correctness reference and actual full-image path. Full-image tests check native output shape, halo coverage, reproducible circuit measurements, uniform-image boundaries, real multispectral TIFF axes, and complete auditable shot counts. Finite-shot estimates are checked against a conservative binomial uncertainty bound rather than assuming noise-free equality.

The live-view integration check starts the real full-image quantum workload and observes running circuits, completed shots and the final saved output. It also checks the absence of image-selection controls and a mobile layout without horizontal overflow.

## Results and limitations

Within one pixel of the approximate catalog rims, QHED F1 is about **0.251**, versus **0.315** for Sobel. Exact-pixel QHED F1 is about 0.081. The method detects terrain and lighting edges alongside crater rims; it is not yet a reliable crater-object detector. The circular catalog labels are not image-traced pixel boundaries and omit some smaller craters, so these metrics also reflect limitations of the reference labels.

No annotations are used for region selection or threshold optimization. This single train-split demonstration is not a held-out performance study. Full run metadata, metrics, the comparison figure and a generated report are in `results/real_case/row0/`.

Dataset: [NASA-IBM AI4Science SomBench WAC Crater Detection](https://huggingface.co/datasets/nasa-ibm-ai4science/Sombench-WAC-Crater-Detection), derived from Robbins (2019), CC BY 4.0.


## User image uploads

The local server accepts PNG/JPEG/WebP/BMP/TIFF uploads, completes orientation, transparency, aspect-preserving resize, grayscale, global percentile contrast and light Gaussian preprocessing, then runs the existing actual QHED inference pipeline. Inputs are capped at 20 MB and 16 million decoded pixels/samples and fitted within 512 pixels per side. The browser displays both preprocessing previews and animates actual gate checkpoints with coordinates matching the uploaded working image. Upload results have no annotation metrics. Private images and artifacts are excluded from Git.

Validation includes 28 passing unit tests and a browser upload run on a 96x64 RGBA fixture, verifying actual measurements, checkpoint playback, invalid-file rejection, reload context and the mobile layout. The fixture executes 140 circuits and 1,146,880 measurement shots.


## Classical detector comparison

Both the lunar case and uploaded images now save and display Sobel, Canny and Robinson outputs beside the measured quantum map. All methods receive the identical grayscale working input. Sobel and Robinson use normalized 3x3 responses with Otsu thresholds; Canny retains the repository's automatic median thresholds. `detector_comparison.json` records the working-input hash, detector policies, edge counts and coverage. Coverage is descriptive, not accuracy; the labeled lunar case retains its catalog boundary scores. The browser upload check verifies each saved classical map against the detector output on the saved quantum input and checks all four comparison panels on desktop and mobile.
