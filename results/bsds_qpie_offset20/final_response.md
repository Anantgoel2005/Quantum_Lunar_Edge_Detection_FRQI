Completed the [20-image QPIE follow-up](<C:/Users/Anant Goel/Documents/Projects/Quantum Edge Detection/Quantum_Lunar_Edge_Detection_FRQI/results/bsds_qpie_offset20/report.md>), adding **45 runs**.

| Metric, all 20 images | Baseline | Minimum subtraction |
|---|---:|---:|
| Image-optimal F1 ↑ | 0.3603 | 0.3618 |
| Boundary AP101 ↑ | 0.2349 | 0.2536 |
| Gradient RMSE ↓ | 14.39 | 10.02 |

**Subtraction improves gradient estimation and AP101, but a primary F1 gain is not established.** On the remaining 15 images, F1 changed by −0.0015, with a 95% interval of [−0.0050, +0.0021].

Defaults remain unchanged. Next: a controlled smoothing comparison of QPIE and exact gradients against Sobel/Robinson.

Verification passed: **47 tests**, **48,000 circuits replayed**, and an isolated rerun matching every count exactly. These remain validation-crop results. Jev’s generic advisory uncertainty and investigations are recorded in the [quality review](<C:/Users/Anant Goel/Documents/Projects/Quantum Edge Detection/Quantum_Lunar_Edge_Detection_FRQI/results/bsds_qpie_offset20/quality_review.md>).
