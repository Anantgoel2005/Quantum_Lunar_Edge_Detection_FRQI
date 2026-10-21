We use **three circuit families, each with four passes: 12 circuit variants per 16×16 image block**. I generated the diagrams from the actual Qiskit builders.

[Open the complete circuit atlas](<C:/Users/Anant Goel/Documents/Projects/Quantum Edge Detection/Quantum_Lunar_Edge_Detection_FRQI/results/circuit_showcase/guide.md>) for all 12 diagrams, formulas, primitive-gate exports and legacy helpers.

![The three live quantum circuits, showing the horizontal offset-1 pass](<C:/Users/Anant Goel/Documents/Projects/Quantum Edge Detection/Quantum_Lunar_Edge_Detection_FRQI/results/circuit_showcase/circuits_overview.png>)

| Circuit family | Qubits | How brightness is stored | What the edge signal means |
|---|---:|---|---|
| **QPIE** | 8 | Amplitudes of position states | Size of neighboring intensity differences |
| **FRQI** | 9 | Angle of one extra brightness qubit | Angle differences, calibrated to intensity differences |
| **NEQR** | 12 | Four extra bits holding 16 brightness levels | Whether neighboring quantized intensities differ |

Read each diagram from left to right:

1. **Prepare the image state.** The blue block creates the encoding. This is where the three families differ most.
2. **Shift the coordinate, for offset 1.** Controlled-X carry gates followed by X increment the column or row register. Offset 0 skips this stage.
3. **Apply Hadamard H.** It transforms neighboring amplitudes into sum and difference channels. Equal neighboring states cancel in the difference channel.
4. **Measure M.** Repeated measurements estimate probabilities. FRQI/NEQR brightness outcomes are summed over when extracting the position response.

The four passes cover every horizontal and vertical neighbor:

| Pass | Hadamard target | Pairs covered |
|---|---|---|
| Horizontal, offset 0 | q0 | Columns (0,1), (2,3), … |
| Horizontal, offset 1 | q0 | Columns (1,2), (3,4), … |
| Vertical, offset 0 | q4 | Rows (0,1), (2,3), … |
| Vertical, offset 1 | q4 | Rows (1,2), (3,4), … |

Here q0–q3 hold the column and q4–q7 hold the row. Shift wraparound pairs are discarded during decoding.

**Why similar gate diagrams give different results:** QPIE interferes intensity amplitudes, FRQI interferes brightness-angle states, and NEQR interferes binary brightness states. For NEQR, distinct brightness states are orthogonal: a small quantized change and a large one have the same ideal directional response.

**What happens outside the circuits:** calibration, halo stitching, combining horizontal/vertical responses, normalization and Otsu thresholding are classical. At the default 8,192 shots per pass, one block uses **four circuits and 32,768 shots**.

**Two distinctions matter:** the live circuits allocate no extra ancilla, and the blue `Initialize` box hides substantial preparation work—hundreds or thousands of primitive gates in the supplied examples. The atlas also explains the older explicit NEQR encoder, reconstruction-plus-classical-gradient pipeline and QPIE ancilla helper; those do not power the running apps.

All 12 illustrated states and measurement laws were checked, alongside 47 existing test executions across the three versions. [Verification and Jev review](<C:/Users/Anant Goel/Documents/Projects/Quantum Edge Detection/Quantum_Lunar_Edge_Detection_FRQI/results/circuit_showcase/quality_review.md>) records the evidence and remaining advisory uncertainty.
