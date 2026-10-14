"""
Noise Models for Quantum Simulation

Provides configurable noise models for AerSimulator:
  - Ideal (no noise)
  - Depolarizing: p in {0.001, 0.005, 0.01, 0.05}
  - Readout error: p in {0.01, 0.05, 0.10}
  - Gate noise (over-rotation / coherent error)
  - Combined: all above simultaneously
"""
from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError
import numpy as np


def get_noise_model(noise_type="ideal", params=None):
    """
    Create a noise model for AerSimulator.
    
    Args:
        noise_type: one of 'ideal', 'depolarizing', 'readout', 'gate', 'combined'
        params: dict with noise parameters
    
    Returns:
        NoiseModel or None (for ideal)
    """
    if noise_type == "ideal":
        return None
    if noise_type not in ('depolarizing', 'readout', 'gate', 'combined'):
        raise ValueError(f'Unknown noise type: {noise_type}')
    
    if params is None:
        params = {}
    
    noise_model = NoiseModel()
    single_error = None
    
    if noise_type == "depolarizing" or noise_type == "combined":
        p = params.get('depolarizing_p', 0.01)
        # Single-qubit depolarizing
        error_1q = depolarizing_error(p, 1)
        single_error = error_1q
        # Two-qubit depolarizing (cx only; ccx is 3-qubit so needs separate handling)
        error_2q = depolarizing_error(p, 2)
        noise_model.add_all_qubit_quantum_error(error_2q, ['cx'])
    
    if noise_type == "readout" or noise_type == "combined":
        p_ro = params.get('readout_p', 0.05)
        # Readout error: probability of bit-flip on measurement
        ro_error = ReadoutError([[1 - p_ro, p_ro], [p_ro, 1 - p_ro]])
        noise_model.add_all_qubit_readout_error(ro_error)
    
    if noise_type == "gate" or noise_type == "combined":
        # Coherent over-rotation error approximated as small depolarizing
        p_gate = params.get('gate_p', 0.005)
        gate_error = depolarizing_error(p_gate, 1)
        single_error = gate_error if single_error is None else single_error.compose(gate_error)

    if single_error is not None:
        noise_model.add_all_qubit_quantum_error(single_error, ['u'])
    
    return noise_model


def get_experiment_noise_configs():
    """
    Get all noise configurations for Experiment 5 (noise simulation).
    
    Returns:
        list of (name, noise_model) tuples
    """
    configs = [
        ("ideal", None),
        ("depol_0.001", get_noise_model("depolarizing", {'depolarizing_p': 0.001})),
        ("depol_0.005", get_noise_model("depolarizing", {'depolarizing_p': 0.005})),
        ("depol_0.01", get_noise_model("depolarizing", {'depolarizing_p': 0.01})),
        ("depol_0.05", get_noise_model("depolarizing", {'depolarizing_p': 0.05})),
        ("readout_0.01", get_noise_model("readout", {'readout_p': 0.01})),
        ("readout_0.05", get_noise_model("readout", {'readout_p': 0.05})),
        ("readout_0.10", get_noise_model("readout", {'readout_p': 0.10})),
        ("gate_0.005", get_noise_model("gate", {'gate_p': 0.005})),
        ("combined", get_noise_model("combined", {
            'depolarizing_p': 0.01, 'readout_p': 0.05, 'gate_p': 0.005
        })),
    ]
    return configs


if __name__ == "__main__":
    configs = get_experiment_noise_configs()
    print(f"Noise configurations: {len(configs)}")
    for name, model in configs:
        print(f"  {name}: {'None' if model is None else 'NoiseModel'}")
    print("Noise models: OK")
