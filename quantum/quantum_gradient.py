"""
Quantum Gradient Operator (Branch B) -- for NEQR-encoded images

Computes pixel differences via quantum operations on NEQR-encoded images.

For NEQR encoding, the gradient can be approximated by:
1. Encoding the image with NEQR
2. Applying a controlled-SWAP or shift operation between adjacent positions
3. Measuring the difference in the intensity register

For simulation feasibility, we use a hybrid approach:
- NEQR encodes the image into quantum state
- We measure and compute gradients classically from the NEQR reconstruction
- This preserves the NEQR encoding step while being simulatable

This is the approach used in Li et al. (2017) for quantum Sobel operators.
"""
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


def quantum_gradient_from_neqr(image, intensity_bits=4, shots=8192, noise_model=None):
    """
    NEQR-based quantum gradient edge detection.
    
    Pipeline:
    1. Encode image with NEQR
    2. Measure to reconstruct pixel values
    3. Compute gradient (Sobel-like) on reconstructed image
    4. The quantum noise from measurement becomes part of the edge detection
    
    This captures the NEQR encoding fidelity + measurement noise effects.
    
    Args:
        image: 2D numpy array (uint8 grayscale)
        intensity_bits: bits for NEQR encoding
        shots: measurement shots
        noise_model: optional noise model
    
    Returns:
        edge_map: 2D edge probability map (float64, 0-1)
        reconstructed: NEQR-reconstructed image
        circuit: the quantum circuit
    """
    from quantum.neqr_encoder import neqr_encode_simplified
    
    h, w = image.shape
    n_pixels = h * w
    
    # Step 1: NEQR encode
    qc, n_pos, n_int = neqr_encode_simplified(image, intensity_bits)
    total_qubits = n_pos + n_int
    
    # Add measurements
    full_qc = QuantumCircuit(total_qubits, total_qubits)
    full_qc.compose(qc, inplace=True)
    full_qc.measure(range(total_qubits), range(total_qubits))
    
    # Step 2: Run simulation
    sim = AerSimulator()
    if noise_model:
        sim = AerSimulator(noise_model=noise_model)
    
    tc = transpile(full_qc, sim)
    result = sim.run(tc, shots=shots).result()
    counts = result.get_counts()
    
    # Step 3: Reconstruct image from NEQR measurements
    max_val = 2 ** n_int - 1
    reconstructed = np.zeros(2 ** n_pos)
    total_counts = np.zeros(2 ** n_pos)
    
    for bitstring, count in counts.items():
        bits = bitstring[::-1]
        if len(bits) >= total_qubits:
            int_bits = bits[:n_int]
            pos_bits = bits[n_int:n_int + n_pos]
            
            pos_idx = int(pos_bits, 2) if pos_bits else 0
            int_val = int(int_bits, 2) if int_bits else 0
            
            if pos_idx < len(reconstructed):
                reconstructed[pos_idx] += int_val * count
                total_counts[pos_idx] += count
    
    mask = total_counts > 0
    reconstructed[mask] /= total_counts[mask]
    reconstructed = reconstructed[:n_pixels].reshape(h, w)
    
    # Scale to 0-1
    recon_norm = reconstructed / max(max_val, 1)
    
    # Step 4: Compute gradient on reconstructed image
    # Use numpy-based Sobel-like gradient
    gx = np.zeros_like(recon_norm)
    gy = np.zeros_like(recon_norm)
    
    # Horizontal gradient
    if w > 1:
        gx[:, 1:] = np.abs(recon_norm[:, 1:] - recon_norm[:, :-1])
    
    # Vertical gradient
    if h > 1:
        gy[1:, :] = np.abs(recon_norm[1:, :] - recon_norm[:-1, :])
    
    # Edge magnitude
    edge_map = np.sqrt(gx ** 2 + gy ** 2)
    
    # Normalize to 0-1
    if edge_map.max() > 0:
        edge_map = edge_map / edge_map.max()
    
    return edge_map, (reconstructed / max(max_val, 1) * 255).astype(np.uint8), full_qc


if __name__ == "__main__":
    from pathlib import Path
    from PIL import Image
    
    img = np.array(Image.open(
        Path(r"E:\projects\Quantum_Image\data\synthetic\images\circle_4x4.png")
    ))
    
    print(f"Testing Quantum Gradient on circle_4x4 (shape={img.shape})")
    edge_map, recon, qc = quantum_gradient_from_neqr(img, intensity_bits=4)
    print(f"Circuit: {qc.num_qubits} qubits")
    print(f"Edge map:\n{np.round(edge_map, 3)}")
    print(f"Reconstructed:\n{recon}")
    print("Quantum gradient: OK")
