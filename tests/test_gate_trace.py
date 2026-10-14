"""Actual checkpoints, unchanged inference measurements, and trace audits."""
import gzip
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from quantum.qhed_circuit import build_qhed_circuit
from quantum.gate_trace import instrument_circuit,extract_trace
from quantum.full_image import run_full_image_qhed


class GateTraceCorrectness(unittest.TestCase):
    def test_actual_checkpoints_match_gate_prefixes_and_counts(self):
        image = np.random.default_rng(42).integers(0,256,(4,4))
        for direction in ('horizontal','vertical'):
            for offset in (0,1):
                original,_,_ = build_qhed_circuit(image,direction,offset)
                traced,description = instrument_circuit(original)
                simulator = AerSimulator(method='statevector',max_parallel_threads=1)
                result = simulator.run(traced,shots=512,seed_simulator=42).result()
                packet = extract_trace(result,0,description)
                plain = simulator.run(original,shots=512,seed_simulator=42).result()
                self.assertEqual(packet['counts'],dict(plain.get_counts()))
                self.assertTrue(packet['measure_sampling'])
                prefix = original.remove_final_measurements(inplace=False)
                prefix.data.clear()
                points = iter(packet['snapshots'])
                initial = next(points)
                np.testing.assert_array_equal(initial['real'],[1]+[0]*15)
                for instruction in original.data:
                    if instruction.operation.name in ('measure','barrier'):
                        continue
                    prefix.append(instruction.operation,instruction.qubits,instruction.clbits)
                    expected = Statevector.from_instruction(prefix).data
                    snapshot = next(points)
                    actual = np.array(snapshot['real'])+1j*np.array(snapshot['imag'])
                    np.testing.assert_allclose(actual,expected,atol=1e-9)
                    self.assertAlmostEqual(snapshot['norm'],1,places=10)
                self.assertEqual(packet['gates'][-1]['name'],'measure')

    def test_trace_matches_the_same_inference_audit(self):
        image = np.arange(64).reshape(8,8).astype(np.uint8)
        packets = []
        with tempfile.TemporaryDirectory() as folder:
            audit = Path(folder)/'counts.gz'
            traces = Path(folder)/'traces.gz'
            maps,meta,_ = run_full_image_qhed(image,tile_size=8,shots=256,batch_tiles=2,
                audit_path=audit,gate_trace=packets.append,trace_audit_path=traces)
            with gzip.open(audit,'rt') as handle:
                records = [json.loads(line) for line in handle]
            with gzip.open(traces,'rt') as handle:
                saved_packets = [json.loads(line) for line in handle]
        self.assertEqual(len(packets),2)
        self.assertEqual(saved_packets,packets)
        self.assertEqual(meta['gate_trace']['representative_blocks'],2)
        for packet in packets:
            self.assertEqual(len(packet['circuits']),4)
            for circuit in packet['circuits']:
                matching = next(r for r in records if r['tile_y']==packet['tile_y'] and r['tile_x']==packet['tile_x']
                    and r['direction']==circuit['metadata']['direction'] and r['pair_offset']==circuit['metadata']['pair_offset'])
                self.assertEqual(circuit['counts'],matching['counts'])
                self.assertEqual(packet['job_id'],matching['job_id'])
        self.assertEqual(maps['strength'].shape,image.shape)


if __name__ == '__main__':
    unittest.main()
