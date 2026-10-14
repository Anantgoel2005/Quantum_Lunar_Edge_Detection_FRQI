"""Hybrid NEQR encoding/measurement followed by a classical forward gradient.

This is not a coherent quantum gradient operator. Under ideal measurement,
once all positions are sampled, the output matches a classical four-bit
quantization plus identical-gradient control.
"""
import numpy as np
from classical.finite_difference import forward_gradient
from quantum.neqr_encoder import run_neqr_verify


def quantum_gradient_from_neqr(image, intensity_bits=4, shots=8192,
                               noise_model=None, seed_simulator=None):
    reconstructed, _, circuit = run_neqr_verify(
        image, intensity_bits, shots, noise_model=noise_model,
        seed_simulator=seed_simulator, return_float=True)
    edge_map = forward_gradient(reconstructed)
    return edge_map, np.rint(reconstructed).astype(np.uint8), circuit
