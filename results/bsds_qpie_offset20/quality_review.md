# QPIE offset follow-up: quality review

User authorization: extend QPIE block-minimum subtraction to the remaining 15 BSDS validation crops using the existing baseline, seeds and budget; compare paired boundary F1 and gradient RMSE. Use Jev planning, implementation, verification and delivery checkpoints and investigate flags.

## Planning and implementation

The original pilot remains read-only. The extension freezes its own protocol, driver hash, parent artifact hashes, source/package versions and input hashes before the new simulations. Sixty baseline records and fifteen existing offset records are reused; forty-five offset runs are added. The first five images motivated this choice, so the remaining fifteen are reported separately. All data remain development validation data, with no new downloads or test-content access.

Jev planning returned investigate with generic uncertainty about requirements clarity (0.62) and evidence sufficiency (0.65), while coverage was 0.87. No specific defect was identified. Scope was made concrete through the frozen 45-run ledger, separate remaining-15 analysis, fixed shot/seeds and image-level sampling. See jev_plan.json.

The first implementation review assessed requirement coverage 0.91 and regression risk 0.15, retaining uncertainty about unnecessary changes (0.22). Changes were inspected: a standalone follow-up runner and statistical tests, with no live detector or original pilot modifications. A supplementary scheduler uses three isolated processes with unique tasks and separate result folders. The serial parent was stopped while its active worker was allowed to finish, and no active worker remained before the parallel scheduler started. Five completed runs were retained. Execution scheduling does not change simulation settings, and no timing ranking is claimed.

The implementation follow-up returned generic uncertainty about coverage (0.46), risk (0.41) and unnecessary changes (0.40), without concrete concerns. Source/protocol guards, unique task ownership, targeted tests and full count replay address the identifiable risks; no additional checkpoint loop was performed. See jev_implementation.json and jev_implementation_followup.json.

Three new statistical tests guard against optimizing each seed before averaging, mismatched pair vectors, and treating a seed matrix as independent image observations. The full FRQI suite passed 47 tests in 5.574 seconds; six boundary tests include fifty random sparse-vs-independent-dense assignment fixtures. Compilation and whitespace checks passed. See tests_frqi.log. The sibling NEQR repository is unchanged and is not involved in these new simulations.

## Concrete reporting issue

The frozen runner's generic raw-summary field improved_images counts positive differences. For RMSE that direction is incorrect. The independent analysis explicitly corrects the verified summary: increased_images always counts positive differences, while improved_images counts lower RMSE or higher F1/AP101. No mean, interval, saved measurement or scientific comparison is changed. The report links the verified summary and explains this correction. Keeping the frozen raw driver/protocol also preserves the exact provenance of already-started simulations.

## Verification and delivery

All 45 new runs completed. Full paired verification passed for 120 records, 48,000 circuits and 393,216,000 simulator shots, with zero magnitude discrepancy on independent replay. Every boundary-count curve and per-run RMSE agreed. The original pilot artifact hashes, source versions, input identities and complete seed/configuration ledger agree. See verification.json.

The independent analysis checked 187 metric cells and nine bootstrap intervals using frequency-weighted resampling arithmetic, and reproduced the original baseline and initial-five effect. The scheduler and frozen driver hashes match. Nine report table rows and eight local links were checked; the three-panel zero-based figure was visually inspected. See summary_verification.json and artifact_verification.json.

Jev verification returned investigate for generic check relevance (0.78) and missing checks (0.53), with claim support 0.89 and no concrete concerns. To address a remaining identifiable scheduling risk, a fresh isolated rerun of case 170057, seed 42 was compared against the concurrent result. All 400 circuit count dictionaries, magnitude/strength maps and boundary-count curves were exactly equal. This is an additional QA simulation, separate from the 45-run scientific extension. See reproduction_verification.json. The follow-up checkpoint is retained as jev_verification_followup.json; no more than two cycles were performed.

Measured interpretation: the remaining-15 primary F1 effect is -0.00153 with interval [-0.00499, +0.00213], so a positive F1 effect is not established. All-20 gradient RMSE decreases from 14.3921 to 10.0160, and descriptive AP101 increases from 0.2349 to 0.2536. These distinct endpoints must not be summarized as either a universal win or no improvement. Detector defaults remain unchanged. Validation-only crop metrics, unadjusted intervals and the first-five-informed hypothesis are disclosed.

The verification follow-up still returned investigate, with relevance 0.70, claim support 0.70 and missing checks 0.44, without specific concerns. These unexplained advisory uncertainties remain unresolved; the measured checks establish the narrower facts above, not official evaluator equivalence or unseen-image generalization.

Jev delivery reviewed the actual report and final Markdown, returning investigate for completeness (0.77) and formatting (0.66), with claim support 0.83 and no concrete concerns. Targeted inspection confirmed all six final-response metric values against the independently validated summary, both absolute artifact links exist, and the table uses proper blank lines and a delimiter row. The final response covers the completed runs, primary/secondary/descriptive outcomes, remaining-15 interval, unchanged defaults, next experiment, verification and validation scope. See final_response_verification.json and jev_delivery.json. Generic Jev uncertainty is retained explicitly; no Jev pass is claimed.
