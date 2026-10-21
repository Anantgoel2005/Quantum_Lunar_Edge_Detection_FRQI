# Controlled filtering quality review

User authorization: run the proposed fixed-grid spatial filtering experiment using saved QPIE maps and equally filtered exact-gradient controls, retain Sobel/Robinson references, compare paired boundary F1/AP101 and gradient error, and use Jev checkpoints with investigation of flagged issues.

## Plan and implementation

The grid was frozen before this evaluation: Gaussian output-magnitude sigma 0, 0.5 and 1 native pixel, radius ceil(3 sigma), half-sample reflection. The exact-gradient magnitude receives the same operation. Filtering precedes per-map maximum normalization and the existing cropped/thinned boundary evaluation. This experiment does not filter the input image or signed gradient components. It uses the same 20 validation cases and three simulator seeds, without new simulations, downloads or test access.

Jev planning returned investigate with no concrete concerns: clarity 0.62, coverage 0.80 and evidence sufficiency 0.67. The scope was resolved into a frozen protocol, 420-record matrix, original input/source hashes, separate matched-target versus raw-target RMSE and image-level excess-gain comparisons. This prevents reduction of smoothing bias from being confused with reduction of estimation error.

Jev implementation reviewed the actual computational sources and tests. It assessed requirement coverage 0.80, regression risk 0.21 and unnecessary changes 0.19, returning investigate for generic regression uncertainty without identifying a specific defect. The new runner and verifier are isolated from live detectors and original experiments. All original inputs are hashed before and after processing. The sigma-zero branch must reproduce all 140 parent curves. The verifier uses independent dense 2D convolution, separate scalar score arithmetic and frequency-weighted bootstrap calculations. These target the identifiable regression risks rather than changing the implementation in response to a score alone.

The full FRQI regression suite passed 52 tests in 6.932 seconds. Five new tests cover separable-vs-dense convolution at corners and interiors, reflective constant/zero maps, exact sigma-zero identity, matched error versus smoothing bias, seed-count averaging before threshold optimization, and rejection of seed pseudoreplication. Eleven focused filtering/boundary tests passed in 0.050 seconds. The boundary tests include fifty small random sparse-versus-dense assignment fixtures. Compilation and whitespace checks passed. See tests.log.

## Interpretation limits

These are development-grid observations on previously used natural-image validation crops, not unseen test performance. All grid settings are reported. Image-optimal F1 is primary; AP101 is descriptive. All 32 paired intervals are exploratory, unadjusted for multiplicity and use twenty images, not sixty independent seeds. Excess F1 gain subtracts the exact control's filtering gain on each image. It does not establish a quantum advantage. The shared boundary matcher is not certified against the Berkeley MATLAB evaluator. No detector defaults are changed.

## Verification and delivery

Final measurements and checkpoint outcomes are recorded after the complete independent replay.

Publication status: development output only. The independent full-grid replay and final report were interrupted; summary.json is provisional and must not be cited as verified final results.
