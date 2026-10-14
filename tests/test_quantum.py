"""Correctness checks using exact statevectors and seeded measurements."""
import unittest
import numpy as np
from qiskit.quantum_info import Statevector
from classical.finite_difference import quantized_gradient
from quantum.neqr_encoder import run_neqr_verify
from quantum.quantum_gradient import quantum_gradient_from_neqr
from quantum.qhed_circuit import build_qhed_circuit, qhed_counts_to_edge_map, run_qhed_combined
from quantum.reconstruction import counts_to_probability_map, threshold_edge_map
from evaluation.metrics import pr_auc, boundary_f1
from quantum.noise_models import get_noise_model


def exact_maps(image):
    maps = []
    for direction in ('horizontal', 'vertical'):
        passes = []
        for offset in (0, 1):
            qc, _, _ = build_qhed_circuit(image, direction, offset)
            counts = Statevector.from_instruction(qc.remove_final_measurements(inplace=False)).probabilities_dict()
            passes.append(qhed_counts_to_edge_map(counts, image.shape, direction, offset))
        maps.append(np.maximum(*passes))
    return maps


class QuantumCorrectness(unittest.TestCase):
    def test_count_integer_order(self):
        expected = np.zeros((2, 4))
        expected.flat[1] = 1
        np.testing.assert_array_equal(counts_to_probability_map({'001': 10}, 3, (2, 4)), expected)

    def test_neqr_asymmetric_roundtrip(self):
        image = np.random.default_rng(7).permutation(16).reshape(4, 4).astype(np.uint8) * 17
        recon, counts, _ = run_neqr_verify(image, shots=8192, seed_simulator=42)
        self.assertEqual(len(counts), 16)
        np.testing.assert_array_equal(image, recon)

    def test_hybrid_matches_quantized_control(self):
        image = np.random.default_rng(8).integers(0, 256, (4, 4), dtype=np.uint8)
        edges, _, _ = quantum_gradient_from_neqr(image, shots=8192, seed_simulator=42)
        np.testing.assert_allclose(edges, quantized_gradient(image), atol=1e-12)

    def test_exact_all_boundaries_rectangular_and_square(self):
        for shape in [(4, 4), (8, 8), (4, 8), (8, 4)]:
            image = np.random.default_rng(42).integers(0, 256, shape).astype(float)
            h_map, v_map = exact_maps(image)
            denom = 2 * np.sum(image ** 2)
            expected_h, expected_v = np.zeros(shape), np.zeros(shape)
            expected_h[:, 1:] = np.diff(image, axis=1) ** 2 / denom
            expected_v[1:, :] = np.diff(image, axis=0) ** 2 / denom
            np.testing.assert_allclose(h_map, expected_h, atol=1e-12)
            np.testing.assert_allclose(v_map, expected_v, atol=1e-12)

    def test_uniform_image_has_no_edges(self):
        for image in [np.zeros((4, 4)), np.full((4, 4), 100.)]:
            h_map, v_map = exact_maps(image)
            np.testing.assert_allclose(h_map, 0, atol=1e-12)
            np.testing.assert_allclose(v_map, 0, atol=1e-12)

    def test_shifted_boundary_is_detected(self):
        image = np.zeros((8, 8))
        image[:, 4:] = 255
        combined, _, vertical = run_qhed_combined(image, shots=8192, seed_simulator=42)
        np.testing.assert_array_equal(np.argwhere(combined > 0), [[i, 4] for i in range(8)])
        self.assertFalse(np.any(vertical))

    def test_seed_repeatability(self):
        image = np.arange(16).reshape(4, 4).astype(float)
        first = run_qhed_combined(image, shots=256, seed_simulator=42)[0]
        second = run_qhed_combined(image, shots=256, seed_simulator=42)[0]
        np.testing.assert_array_equal(first, second)

    def test_invalid_inputs(self):
        for image in [np.ones((3, 4)), np.empty((0, 4)), np.full((4, 4), np.nan), -np.ones((4, 4))]:
            with self.assertRaises(ValueError):
                build_qhed_circuit(image)
        with self.assertRaises(ValueError):
            build_qhed_circuit(np.ones((4, 4)), 'diagonal')
        with self.assertRaises(ValueError):
            run_neqr_verify(np.ones((4, 4)), intensity_bits=0)

    def test_otsu_separates_clusters_without_rounding(self):
        values = np.array([[0., 0.0001, 0.01, 0.012]])
        binary, threshold = threshold_edge_map(values)
        np.testing.assert_array_equal(binary, [[0, 0, 255, 255]])
        self.assertGreater(threshold, 0.0001)
        self.assertLess(threshold, 0.01)
        self.assertFalse(np.any(threshold_edge_map(np.zeros((4, 4)))[0]))

    def test_binary_masks_and_constant_score_baseline(self):
        gt = np.array([[0, 1], [0, 0]], dtype=np.uint8)
        self.assertEqual(boundary_f1(gt, gt)[0], 1)
        self.assertEqual(pr_auc(np.zeros((2, 2)), gt)[0], 0.25)
        self.assertEqual(pr_auc(gt.astype(float), gt)[0], 1)

    def test_noisy_primitive_execution(self):
        image = np.arange(16).reshape(4, 4).astype(float)
        ideal = run_qhed_combined(image, shots=512, seed_simulator=42)[0]
        noisy = run_qhed_combined(image, shots=512, seed_simulator=42,
            noise_model=get_noise_model('readout', {'readout_p': 0.1}))[0]
        self.assertTrue(np.all(np.isfinite(noisy)))
        self.assertFalse(np.array_equal(ideal, noisy))


if __name__ == '__main__':
    unittest.main()
