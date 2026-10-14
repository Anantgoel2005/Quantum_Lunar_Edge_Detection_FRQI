"""Shared simulation and input validation for the quantum pipelines."""
import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator

PRIMITIVE_BASIS = ['u', 'cx']


def validate_image(image, power_of_two=False):
    image = np.asarray(image)
    if image.ndim != 2 or image.size < 2 or min(image.shape) < 1:
        raise ValueError('Expected a nonempty 2D grayscale image with at least two pixels')
    if not np.all(np.isfinite(image)) or np.any(image < 0):
        raise ValueError('Image intensities must be finite and nonnegative')
    if power_of_two and any(size & (size - 1) for size in image.shape):
        raise ValueError('QHED requires power-of-two image height and width')
    return image


def simulate_counts(circuit, shots, noise_model=None, seed_simulator=None):
    if not isinstance(shots, (int, np.integer)) or shots <= 0:
        raise ValueError('shots must be a positive integer')
    simulator = AerSimulator(noise_model=noise_model)
    if noise_model is not None:
        compiled = transpile(circuit, basis_gates=PRIMITIVE_BASIS, seed_transpiler=seed_simulator)
    else:
        compiled = transpile(circuit, simulator, seed_transpiler=seed_simulator)
    return simulator.run(compiled, shots=int(shots), seed_simulator=seed_simulator).result().get_counts()
