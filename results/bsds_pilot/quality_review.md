# Quality checkpoints and investigations

This log distinguishes measured checks from advisory Jev judgments. The original SomBench benchmark remains separate and unchanged.

## Plan and implementation

Jev reviewed the initial plan and implementation, then the revised frozen plan and execution driver. Its responses requested investigation of requirements clarity, evidence sufficiency, requirement coverage and unnecessary changes, without identifying concrete defects. The implementation follow-up assessed regression risk as low but retained generic uncertainty about requirement coverage and unnecessary changes. These responses are advisory, not a certification or an execution gate.

The resulting investigations established:

- Twenty validation IDs and the five-image efficiency subset were selected by a fixed hash ranking before opening labels. Test image and annotation contents remain untouched.
- The final protocol freezes 240 quantum runs, 31 thresholds, three widely separated seeds, source hashes, package versions and a matched total-shot comparison. No live detector source was changed.
- The initially considered Higra matcher terminated its process on minimal identity fixtures in this Windows environment. It was replaced before the protocol freeze with a SciPy sparse assignment implementation. Fifty random small examples agree with an independent dense assignment solver, with additional identity, empty-mask, one-to-one and multi-annotator tests.
- The FRQI repository passed 44 tests and the NEQR repository passed 32 tests, for 76 unique tests. See regression_tests.json and tests_frqi.log. Six targeted BSDS tests also passed after interruption recovery. Compilation, dependency consistency and whitespace checks passed.
- A tool interruption damaged one completed count audit and several ancillary files. The damaged run and original logs were preserved under interrupted_artifacts; 28 intact runs were retained after validation. The damaged run was rerun, reproducing its previous map and all boundary counts exactly. README and dataset inventory helper were restored; frozen detector and pilot sources retained their hashes. See interruption_integrity.json.
- Each strength map is normalized by its own maximum, so thresholds represent relative image strength. Canny is the existing automatic binary baseline; its repeated threshold entries do not constitute a tuned precision–recall sweep. The report makes both limitations explicit.

## Interpretation boundaries

These are native-crop validation diagnostics with custom BSDS-style matching and AP101, not official full-image BSDS500 ODS/OIS/AP scores. The three seeds are averaged within images; they do not increase the number of independent images. The five-image bootstrap comparisons are exploratory and unadjusted for multiple comparisons. QPIE/FRQI gradient RMSE and NEQR quantized-inequality RMSE use different operator units. Concurrent ideal simulator runs do not establish timing or quantum hardware advantage.

## Verification and delivery

The full matrix completed and passed count replay: 240 quantum runs, 340 total maps, 165,120 circuits and 786,383,040 shots. Maximum magnitude discrepancy was 8.526512829121202e-14. Every saved 31-threshold count curve was recomputed. No test image or annotation contents were downloaded. See verification.json.

Jev delivery initially returned investigate for completeness and formatting, with claim support 0.85 and no concrete concerns. The final response was revised into explicit Markdown with the measured comparison table, dataset recommendation, next experiment, verification and scope limits. Absolute artifact links and all table values were checked. The final follow-up response is retained in jev_delivery_followup.json; delivery scores are advisory and do not replace the evidence above.

The delivery follow-up still returned investigate, with generic uncertainty about completeness (0.79), claim support (0.66) and formatting (0.74), again without concrete concerns. All five response table values match summary.json, both absolute links resolve, and the full report supplies the remaining method/provenance details. This unexplained model disagreement remains unresolved; no Jev pass is claimed, and no further checkpoint loop was performed.

The independent summary verifier passed all 750 metric cells (including ten operator-RMSE averages), four bootstrap intervals, 40 raw asset hashes, 40 pixel hashes, all 20 raw image/MAT crop derivations, source/package identities and fresh regeneration of all 100 classical/control maps. Its first ad-hoc inequality check used floor(image/16), which disagreed with the encoder specification floor(image/255*15); correcting this verifier assumption produced exact equality. No benchmark result needed changing. See summary_verification.json.

The input montage, main comparison and paired-effect figures were visually inspected. Eight main table rows match the summary and all six local report links resolve. The main figure caption was clarified so only quantum curves imply three seed repetitions. See artifact_verification.json.

Jev verification initially returned investigate with generic uncertainty about check relevance, claim support and missing checks, and no concrete concerns. Targeted follow-up added fresh classical/control recomputation, independent RMSE aggregation, report table/link checks and caption clarification. The second evaluation increased claim support to 0.83 but still returned investigate for check relevance (0.77) and missing checks (0.34). These uncalibrated advisory scores do not explain a specific missing check. The two-cycle limit was respected; the measured evidence and explicit scope limits above support delivery, with generic Jev uncertainty unresolved. Raw responses are saved as jev_verification.json and jev_verification_followup.json.
