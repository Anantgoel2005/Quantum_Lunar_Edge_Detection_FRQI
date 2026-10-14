"""
QPIE Encoder — Quantum Probability Image Encoding (Branch A)

Encodes pixel intensity as probability amplitudes:
    |psi> = (1/C) * SUM_{x,y} I(x,y) |x>|y>

where C = sqrt(SUM I(x,y)^2) is the normalisation constant.

The position is encoded in computational basis states,
and the amplitude at each basis state is proportional to pixel intensity.

For an NxN image: ceil(log2(N^2)) qubits for position.
"""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import Initialize


def qpie_encode(image, normalize=True):
    """
    Create a quantum circuit that encodes a grayscale image using QPIE.
    
    Args:
        image: 2D numpy array (grayscale, any dtype)
        normalize: If True, normalize pixel values to valid amplitudes
    
    Returns:
        qc: QuantumCircuit with the image encoded as amplitudes
        n_qubits: number of qubits used for position encoding
    """
    assert image.ndim == 2, f"Expected 2D image, got shape {image.shape}"
    
    h, w = image.shape
    n_pixels = h * w
    
    # Number of qubits needed
    n_qubits = int(np.ceil(np.log2(n_pixels)))
    n_states = 2 ** n_qubits
    
    # Flatten image to 1D state vector
    flat = image.flatten().astype(np.float64)
    
    # Pad to power of 2 if needed
    if len(flat) < n_states:
        flat = np.pad(flat, (0, n_states - len(flat)))
    
    # Normalize to unit vector (valid quantum state)
    if normalize:
        norm = np.linalg.norm(flat)
        if norm > 0:
            flat = flat / norm
        else:
            # All-zero image: use uniform superposition
            flat = np.ones(n_states) / np.sqrt(n_states)
    
    # Create circuit with Initialize gate
    qc = QuantumCircuit(n_qubits, name="QPIE")
    init_gate = Initialize(flat)
    qc.append(init_gate, range(n_qubits))
    
    return qc, n_qubits


def qpie_encode_with_ancilla(image):
    """
    Create QPIE circuit with one ancilla qubit for QHED.
    
    The ancilla qubit is added at position 0 (least significant).
    Position qubits are at positions 1 to n_pos.
    
    Returns:
        qc: QuantumCircuit (ancilla + position qubits)
        n_pos_qubits: number of position qubits
        ancilla_idx: index of ancilla qubit
    """
    h, w = image.shape
    n_pixels = h * w
    n_pos_qubits = int(np.ceil(np.log2(n_pixels)))
    n_states = 2 ** n_pos_qubits
    
    # Flatten and normalize
    flat = image.flatten().astype(np.float64)
    if len(flat) < n_states:
        flat = np.pad(flat, (0, n_states - len(flat)))
    
    norm = np.linalg.norm(flat)
    if norm > 0:
        flat = flat / norm
    else:
        flat = np.ones(n_states) / np.sqrt(n_states)
    
    # Total qubits: position + 1 ancilla
    total_qubits = n_pos_qubits + 1
    ancilla_idx = 0  # ancilla is qubit 0
    
    # Build state: ancilla|0> tensor product with image state
    # |0>|psi_image> = [psi_0, 0, psi_1, 0, ..., psi_{N-1}, 0]
    full_state = np.zeros(2 ** total_qubits)
    for i in range(n_states):
        # ancilla=0, position=i => index = i*2 + 0 = 2*i
        full_state[2 * i] = flat[i]
    
    qc = QuantumCircuit(total_qubits, name="QPIE+Ancilla")
    init_gate = Initialize(full_state)
    qc.append(init_gate, range(total_qubits))
    
    return qc, n_pos_qubits, ancilla_idx


if __name__ == "__main__":
    # Test with synthetic 4x4 circle
    from pathlib import Path
    from PIL import Image
    
    img_path = Path(r"E:\projects\Quantum_Image\data\synthetic\images\circle_4x4.png")
    img = np.array(Image.open(img_path)).astype(np.float64)
    
    qc, n_qubits = qpie_encode(img)
    print(f"Image shape: {img.shape}")
    print(f"Position qubits: {n_qubits}")
    print(f"Circuit depth: {qc.depth()}")
    print(f"Circuit width: {qc.num_qubits}")
    
    qc2, n_pos, anc = qpie_encode_with_ancilla(img)
    print(f"\nWith ancilla:")
    print(f"  Position qubits: {n_pos}")
    print(f"  Ancilla index: {anc}")
    print(f"  Total qubits: {qc2.num_qubits}")
    print(f"  Circuit depth: {qc2.depth()}")
    print("QPIE encoder: OK")
