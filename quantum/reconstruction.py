"""
Reconstruction -- Convert quantum measurement counts to edge maps.

Utility functions for post-processing quantum circuit outputs
into edge detection images.
"""
import numpy as np


def counts_to_probability_map(counts, n_qubits, image_shape):
    """
    Convert measurement counts to a probability map.
    
    Args:
        counts: dict of bitstring -> count
        n_qubits: number of qubits
        image_shape: (height, width) tuple
    
    Returns:
        prob_map: 2D array with measurement probabilities
    """
    h, w = image_shape
    n_pixels = h * w
    n_states = 2 ** n_qubits
    
    total = sum(counts.values())
    probs = np.zeros(n_states)
    
    for bitstring, count in counts.items():
        idx = int(bitstring[::-1], 2)  # Reverse Qiskit ordering
        if idx < n_states:
            probs[idx] = count / total
    
    return probs[:n_pixels].reshape(h, w)


def threshold_edge_map(continuous_map, method="otsu"):
    """
    Threshold a continuous edge probability map to binary.
    
    Args:
        continuous_map: 2D float array
        method: 'otsu', 'median', or float value
    
    Returns:
        binary: 2D uint8 array (0 or 255)
        threshold: the threshold value used
    """
    if method == "otsu":
        # Simple Otsu-like: maximize inter-class variance
        flat = continuous_map.flatten()
        flat = flat[flat > 0]  # Only non-zero
        if len(flat) == 0:
            return np.zeros_like(continuous_map, dtype=np.uint8), 0
        threshold = np.mean(flat)
    elif method == "median":
        flat = continuous_map.flatten()
        flat = flat[flat > 0]
        threshold = np.median(flat) if len(flat) > 0 else 0.5
    elif isinstance(method, (int, float)):
        threshold = method
    else:
        threshold = 0.5
    
    binary = (continuous_map >= threshold).astype(np.uint8) * 255
    return binary, threshold


def confidence_map(edge_probs, n_trials_results=None):
    """
    Create a confidence map from edge probabilities.
    
    If multiple trial results are provided, computes mean and std
    at each pixel for a full confidence map.
    
    Args:
        edge_probs: 2D array of edge probabilities (single trial)
        n_trials_results: optional list of 2D arrays from multiple trials
    
    Returns:
        mean_map: mean edge probability
        std_map: standard deviation (confidence width)
    """
    if n_trials_results is not None:
        stack = np.stack(n_trials_results, axis=0)
        return np.mean(stack, axis=0), np.std(stack, axis=0)
    
    return edge_probs, np.zeros_like(edge_probs)
