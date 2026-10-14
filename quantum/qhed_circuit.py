"""
QHED Circuit -- Quantum Hadamard Edge Detection (Yao et al., 2017)

The canonical QHED algorithm:
1. Encode image using QPIE (amplitude encoding)
2. Apply Hadamard to the least significant position qubit
3. Measure -- edge pixels show up when ancilla = |1>

The Hadamard creates interference between adjacent pixel amplitudes:
  H|0> = (|0> + |1>) / sqrt(2)
  H|1> = (|0> - |1>) / sqrt(2)

Adjacent pixels with amplitudes a, b:
  a == b  -> amplitudes cancel  -> P(edge) ~ 0
  a != b  -> amplitudes reinforce -> P(edge) ~ |a-b|^2
"""
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


def build_qhed_circuit(image, direction="horizontal"):
    """
    Build the full QPIE + QHED circuit for edge detection.
    
    Args:
        image: 2D numpy array (grayscale)
        direction: 'horizontal' or 'vertical' -- which position qubit gets H
    
    Returns:
        qc: complete quantum circuit with measurements
        n_qubits: total number of qubits
        edge_qubit: index of the qubit that indicates edges
    """
    h, w = image.shape
    n_pixels = h * w
    n_qubits = int(np.ceil(np.log2(n_pixels)))
    
    # Flatten and normalise
    flat = image.flatten().astype(np.float64)
    n_states = 2 ** n_qubits
    if len(flat) < n_states:
        flat = np.pad(flat, (0, n_states - len(flat)))
    
    norm = np.linalg.norm(flat)
    if norm > 0:
        flat = flat / norm
    else:
        flat = np.ones(n_states) / np.sqrt(n_states)
    
    # Build circuit
    qc = QuantumCircuit(n_qubits, n_qubits, name="QPIE_QHED")
    
    # Step 1: QPIE amplitude encoding via Initialize
    from qiskit.circuit.library import Initialize
    init_gate = Initialize(flat)
    qc.append(init_gate, range(n_qubits))
    qc.barrier()
    
    # Step 2: Apply Hadamard to position qubit for edge detection
    # For NxN image with row-major flattening:
    #   qubit 0 = least significant bit -> adjacent columns
    #   qubit 1 = next bit -> adjacent rows (for power-of-2 widths)
    if direction == "horizontal":
        edge_qubit = 0  # detects horizontal (column-adjacent) differences
    elif direction == "vertical":
        edge_qubit = 1 if n_qubits > 1 else 0
    else:
        edge_qubit = 0
    
    qc.h(edge_qubit)
    qc.barrier()
    
    # Step 3: Measure all qubits
    qc.measure(range(n_qubits), range(n_qubits))
    
    return qc, n_qubits, edge_qubit


def run_qhed(image, shots=8192, direction="horizontal", noise_model=None):
    """
    Run the full QPIE + QHED pipeline and return edge probability map.
    
    Args:
        image: 2D numpy array (grayscale, uint8)
        shots: number of measurement shots
        direction: 'horizontal' or 'vertical'
        noise_model: optional Qiskit noise model
    
    Returns:
        edge_probs: 2D array same size as image, with edge probabilities [0,1]
        counts: raw measurement counts
        circuit: the quantum circuit used
    """
    h, w = image.shape
    n_pixels = h * w
    n_qubits = int(np.ceil(np.log2(n_pixels)))
    n_states = 2 ** n_qubits
    
    # Build circuit
    qc, _, edge_qubit = build_qhed_circuit(image, direction)
    
    # Run on AerSimulator
    sim = AerSimulator()
    if noise_model:
        sim = AerSimulator(noise_model=noise_model)
    
    tc = transpile(qc, sim)
    result = sim.run(tc, shots=shots).result()
    counts = result.get_counts()
    
    # Reconstruct edge probability map
    edge_probs = np.zeros(n_states)
    total = sum(counts.values())
    
    for bitstring, count in counts.items():
        # Qiskit returns bitstrings in reverse order
        bits = bitstring[::-1]
        idx = int(bits, 2) if len(bits) == n_qubits else 0
        
        # Check if the edge_qubit is |1> (indicates edge)
        if len(bits) > edge_qubit and bits[edge_qubit] == '1':
            # This measurement indicates an edge at this position
            # Get the position by zeroing the edge qubit
            pos_bits = list(bits)
            pos_bits[edge_qubit] = '0'
            pos_idx = int(''.join(pos_bits), 2)
            edge_probs[pos_idx] += count / total
    
    # Reshape to image size
    edge_map = edge_probs[:n_pixels].reshape(h, w)
    
    return edge_map, counts, qc


def run_qhed_combined(image, shots=8192, noise_model=None):
    """
    Run QHED for both horizontal and vertical directions and combine.
    
    This gives a more complete edge map by detecting edges in both directions.
    
    Returns:
        combined_map: 2D edge probability map (max of H and V)
        h_map: horizontal edge map
        v_map: vertical edge map
    """
    h_map, _, _ = run_qhed(image, shots, "horizontal", noise_model)
    v_map, _, _ = run_qhed(image, shots, "vertical", noise_model)
    
    combined = np.maximum(h_map, v_map)
    return combined, h_map, v_map


if __name__ == "__main__":
    from pathlib import Path
    from PIL import Image
    
    # Test on 4x4 circle
    img = np.array(Image.open(
        Path(r"E:\projects\Quantum_Image\data\synthetic\images\circle_4x4.png")
    )).astype(np.float64)
    
    print(f"Testing QHED on circle_4x4 (shape={img.shape})")
    edge_map, counts, qc = run_qhed(img, shots=8192)
    print(f"Circuit: {qc.num_qubits} qubits, depth={qc.depth()}")
    print(f"Edge map shape: {edge_map.shape}")
    print(f"Edge map range: [{edge_map.min():.4f}, {edge_map.max():.4f}]")
    print(f"Edge map:\n{np.round(edge_map, 3)}")
    
    # Test combined
    combined, h_map, v_map = run_qhed_combined(img, shots=8192)
    print(f"\nCombined map:\n{np.round(combined, 3)}")
    print("QHED circuit: OK")
