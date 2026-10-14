"""Read-only diagnostics for the pulled source; writes only analysis_checks.json."""
import ast
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import qiskit
import qiskit_aer
from qiskit import transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from quantum.neqr_encoder import run_neqr_verify
from quantum.qhed_circuit import build_qhed_circuit, run_qhed, run_qhed_combined, qhed_counts_to_edge_map
from quantum.quantum_gradient import quantum_gradient_from_neqr
from quantum.reconstruction import counts_to_probability_map
from classical.classical_pipeline import run_classical_pipeline

out = {'versions': {'python': sys.version.split()[0], 'qiskit': qiskit.__version__,
                    'qiskit_aer': qiskit_aer.__version__, 'numpy': np.__version__}}
paths = list(ROOT.rglob('*.py'))
paths = [p for p in paths if '.venv' not in p.parts and p != Path(__file__).resolve()]
for path in paths:
    ast.parse(path.read_text(encoding='utf-8'))
out['source_syntax'] = {'parsed_files': len(paths), 'errors': 0}

image = (np.array([3, 1, 7, 0, 8, 14, 2, 10, 6, 11, 15, 4, 13, 5, 12, 9]).reshape(4, 4) * 17).astype(np.uint8)
recon, counts, _ = run_neqr_verify(image, intensity_bits=4, shots=16384)
corrected = np.zeros(16, dtype=np.uint8)
for bitstring in counts:
    value = int(bitstring, 2)
    corrected[value >> 4] = (value & 15) * 17
out['neqr_roundtrip'] = {
    'input': image.tolist(), 'current_reconstruction': recon.tolist(),
    'current_mae': float(np.mean(np.abs(image.astype(float) - recon))),
    'integer_decoding_mae': float(np.mean(np.abs(image.astype(float) - corrected.reshape(4, 4)))),
    'observed_positions': len(counts), 'shots': 16384}
_, gradient_recon, _ = quantum_gradient_from_neqr(image, intensity_bits=4, shots=16384)
out['neqr_roundtrip']['gradient_branch_reconstruction_mae'] = float(
    np.mean(np.abs(image.astype(float) - gradient_recon)))

h_map, counts, _ = run_qhed(image, shots=16384, direction='horizontal')
decoded = qhed_counts_to_edge_map(counts, image.shape, 'horizontal').flatten()
out['qhed_position_decoding'] = {'current_nonzero_positions': np.flatnonzero(h_map).tolist(),
    'integer_decoded_nonzero_positions': np.flatnonzero(decoded).tolist(),
    'maps_equal': bool(np.allclose(h_map.flatten(), decoded))}

out['count_decoding'] = {'input_counts': {'001': 100}, 'expected_flat_index': 1,
    'actual_flat_index': int(np.argmax(counts_to_probability_map({'001': 100}, 3, (2, 4))))}

rows = np.tile(np.arange(8, dtype=float)[:, None], (1, 8))
qc, _, edge_qubit = build_qhed_circuit(rows, 'vertical')
probs = Statevector.from_instruction(qc.remove_final_measurements(inplace=False)).probabilities()
out['vertical_gradient'] = {'selected_qubit': edge_qubit, 'required_row_lsb': 3,
    'exact_edge_probability': float(sum(p for i, p in enumerate(probs) if i & (1 << edge_qubit)))}

step = np.zeros((8, 8), dtype=np.uint8)
step[:, 4:] = 255
qc, _, edge_qubit = build_qhed_circuit(step, 'horizontal')
probs = Statevector.from_instruction(qc.remove_final_measurements(inplace=False)).probabilities()
combined, _, _ = run_qhed_combined(step, shots=16384)
out['uncovered_pair_boundary'] = {
    'description': '8x8 image: columns 0-3 dark, columns 4-7 bright',
    'exact_horizontal_edge_probability': float(sum(p for i, p in enumerate(probs) if i & 1)),
    'combined_nonzero_pixels': int(np.count_nonzero(combined))}

qc, _, _ = build_qhed_circuit(np.arange(64).reshape(8, 8).astype(float))
native = transpile(qc, AerSimulator(), seed_transpiler=42)
decomposed = transpile(qc, basis_gates=['u', 'cx'], optimization_level=1, seed_transpiler=42)
out['qhed_resource_comparison'] = {
    'aer_native_depth': native.depth(), 'aer_native_ops': dict(native.count_ops()),
    'u_cx_depth': decomposed.depth(), 'u_cx_ops': dict(decomposed.count_ops())}

classical = run_classical_pipeline(image)
out['classical_smoke'] = {name: list(value.shape) for name, value in classical.items()}

tables = {}
for path in sorted((ROOT / 'results' / 'tables').glob('*.csv')):
    with path.open(newline='') as handle:
        records = list(csv.DictReader(handle))
    entry = {'rows': len(records)}
    if records and 'size' in records[0]:
        entry['size_counts'] = dict(Counter(r['size'] for r in records))
    if records and 'f1_exact_mean' in records[0]:
        groups = defaultdict(list)
        for record in records:
            groups[(record['method'], record.get('size', 'all'))].append(float(record['f1_exact_mean']))
        entry['f1_by_method_size'] = [
            {'method': key[0], 'size': key[1], 'n': len(vals), 'mean': float(np.mean(vals))}
            for key, vals in groups.items()]
    if path.name == 'exp8_sombench_benchmark.csv':
        entry['unique_patches'] = len(set(r['patch'] for r in records))
    tables[path.name] = entry
out['table_audit'] = tables

out['data_audit'] = {}
for name in ['synthetic/images', 'synthetic/masks', 'sombench/patches', 'sombench/masks',
             'sombench/images', 'sombench/annotations']:
    folder = ROOT / 'data' / name
    out['data_audit'][name] = len(list(folder.glob('*'))) if folder.exists() else 0

destination = ROOT / 'report' / 'corrected_checks.json'
destination.write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps(out, indent=2))
