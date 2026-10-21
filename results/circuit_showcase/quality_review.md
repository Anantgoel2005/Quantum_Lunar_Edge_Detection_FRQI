# Circuit atlas quality review

The user requested a showcase and explanation of all quantum circuits used by the project. The live source review established three encoding families, each with four H/V and pair-offset passes. Retained legacy encoders, reconstruction experiments and analytical references are identified separately from the current apps.

## Planning and implementation

Jev planning returned investigate with generic uncertainty about clarity (0.41) and evidence sufficiency (0.60), and coverage 0.81. No specific concern was identified. Scope was made explicit: twelve native 16×16-block variants, eight/nine/twelve logical qubits, source-derived diagrams, three primitive-basis examples, independent state/probability verification and separate legacy-helper documentation.

Jev implementation inspected the actual generator and source findings, returning investigate with coverage 0.64, regression risk 0.29 and unnecessary changes 0.35, without concrete defects. The generator writes only to this standalone atlas; it does not change detector sources, running servers or existing experiments. Builder and full-image source hashes were recorded and checked again. Per-encoding subprocesses isolate Python imports, and each variant's qubit count and measurement wiring were asserted.

The source-based checks distinguish native Initialize from a hardware gate decomposition, position-register H from brightness gates, simulator checkpoint instructions from physical gates, live NEQR inequality from the older classical-gradient-after-reconstruction baseline, and unused ancilla helpers from the live ancilla-free topology. These are the principal technical ambiguity risks identified during inspection.

## Measured verification

All twelve preparation vectors and post-H states agree with independently calculated states and coordinate permutations. Maximum state-amplitude discrepancy is 6.990237433215068e-17. All twelve accepted-channel probability laws agree, with maximum discrepancy 3.0357660829594124e-18. All three primitive u/cx decompositions preserve the premeasurement state up to global phase; numerical fidelities are within rounding error of one. The explicit two-bit 2×2 NEQR and unused QPIE-ancilla example also passed state checks.

Each live diagram is derived from its Qiskit operations; Initialize is abstracted as one labeled preparation block, barriers are omitted, and terminal measurement gates are grouped in one column. The combined overview was visually inspected for wire roles, gate connections and label legibility. The diagrams are not full primitive-gate drawings. Compilation and whitespace checks passed.

Qiskit issued a cp1252 terminal-encoding warning when formatting text diagrams and selected UTF-8 instead. The generated text files were explicitly written as UTF-8; circuit validation completed successfully.

See verification.json and the encoding-specific JSON manifests for actual checks, source hashes, primitive counts and per-variant gate records. Final artifact checks and advisory delivery findings are appended below.

All twelve SVG documents parse as XML; all 26 guide links resolve. Three preparation/decomposition table rows exactly match generated metadata. QASM exports have OpenQASM 3 headers. The compiled circuits were state-checked before export; QASM text was not imported again because the optional QASM3 importer is absent. No serialization roundtrip claim is made.

The verification follow-up still returned generic investigate signals (relevance 0.67, claim support 0.72, missing checks 0.41) without concrete concerns. These scores do not explain a specific absent check. The measured scope is limited to the illustrated source circuits and relevant regression fixtures, not universal algorithm correctness or hardware execution.

Jev delivery reviewed the actual final Markdown and artifact evidence, returning investigate for completeness (0.71), claim support (0.56) and formatting (0.58), again without concrete concerns. Targeted final inspection confirmed all three absolute artifact/image references exist, both tables have proper blank lines, all encoding qubit counts and four-pass/H-target mappings match generated circuit metadata, and all 47 test executions are confirmed in their logs. The text distinguishes live versus retained circuits, native versus primitive preparation, and classical versus measured quantum work. See final_response_verification.json. Generic advisory uncertainty remains unresolved; no Jev pass or certification is claimed.

Jev verification returned investigate only for generic missing-check uncertainty (0.27), while relevance was 0.84 and claim support 0.89, with no concrete concerns. Follow-up ran the existing quantum and gate-trace tests separately in all three repositories: 13 QPIE tests passed in 3.472 seconds, 17 FRQI in 4.103 seconds, and 17 NEQR in 4.391 seconds. These are 47 test executions, including shared tests; they are not 47 distinct scientific properties. They cover uniform/zero cancellation, all neighbor offsets, rectangular shapes, exact encoding, classical hybrid controls, measured halo stitching and checkpoint consistency. Logs are qpie_tests.log, frqi_tests.log and neqr_tests.log. The two-cycle verification limit was respected; raw responses are retained beside this log.
