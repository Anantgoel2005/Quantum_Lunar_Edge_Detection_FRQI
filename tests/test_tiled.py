"""Native-resolution tiling, shot behavior, and Qiskit equivalence tests."""
import unittest
import numpy as np
from qiskit.quantum_info import Statevector
from quantum.qhed_circuit import build_qhed_circuit
from quantum.tiled import qhed_patch_probabilities, neqr_patch, tiled_quantum_edges
from classical.finite_difference import forward_gradient, quantized_gradient


class TiledCorrectness(unittest.TestCase):
    def test_fast_probabilities_match_qiskit(self):
        for shape in [(4,4),(8,8),(4,8)]:
            image = np.random.default_rng(42).integers(0,256,shape).astype(float)
            for direction in ('horizontal','vertical'):
                for offset in (0,1):
                    qc,_,_ = build_qhed_circuit(image,direction,offset)
                    actual = Statevector.from_instruction(qc.remove_final_measurements(inplace=False)).probabilities().reshape(shape)
                    fast,_ = qhed_patch_probabilities(image,direction,offset)
                    np.testing.assert_allclose(fast,actual,atol=1e-12)

    def test_native_shape_and_no_seam_errors(self):
        image = np.random.default_rng(7).integers(0,256,(23,37),dtype=np.uint8)
        for size in (4,8,16):
            maps,info = tiled_quantum_edges(image,tile_size=size,shots=4096)
            np.testing.assert_allclose(maps['qhed_exact'],forward_gradient(image),atol=1e-12)
            np.testing.assert_allclose(maps['neqr_exact'],quantized_gradient(image),atol=1e-12)
            self.assertEqual(maps['qhed_sampled'].shape,image.shape)
            self.assertGreaterEqual(info['neqr_position_coverage'],0)
            self.assertLessEqual(info['neqr_position_coverage'],1)

    def test_uniform_image_no_artificial_tile_edges(self):
        for value in (0,93,255):
            maps,_ = tiled_quantum_edges(np.full((19,25),value),tile_size=8,shots=8192)
            for edges in maps.values():
                self.assertFalse(np.any(edges))

    def test_low_shot_neqr_reports_unseen_positions(self):
        image = np.full((16,16),255,dtype=np.uint8)
        reconstructed,coverage = neqr_patch(image,shots=8,seed=42)
        self.assertLessEqual(np.count_nonzero(coverage),8)
        self.assertTrue(np.all(reconstructed[~coverage]==0))

    def test_reproducible_sampling_and_invalid_tile_size(self):
        image = np.arange(64).reshape(8,8).astype(np.uint8)
        first,_ = tiled_quantum_edges(image,tile_size=8,shots=512,seed=42)
        second,_ = tiled_quantum_edges(image,tile_size=8,shots=512,seed=42)
        np.testing.assert_array_equal(first['qhed_sampled'],second['qhed_sampled'])
        with self.assertRaises(ValueError):
            tiled_quantum_edges(image,tile_size=6)


if __name__ == '__main__':
    unittest.main()
