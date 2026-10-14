"""
NEQR Encoder -- Novel Enhanced Quantum Representation (Zhang et al., 2013)

NEQR stores exact binary intensity in the computational basis:
    |Q> = (1/sqrt(N)) * SUM_{YX} |f(Y,X)>|YX>

where:
    |f(Y,X)> = |c7 c6 c5 c4 c3 c2 c1 c0>  (8-qubit binary intensity register)
    |YX>     = position in computational basis

State preparation uses multi-controlled CNOT gates per pixel.
NEQR does NOT use RY rotations or angle mappings.

For an NxN 8-bit image:
    Position qubits: ceil(log2(N^2))
    Intensity qubits: 8 (for 8-bit grayscale)
    Total: position + intensity qubits (+ ancilla for gradient)
"""
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


def neqr_encode(image, intensity_bits=8):
    """
    Create a quantum circuit that encodes a grayscale image using NEQR.
    
    For small images (4x4, 8x8), this is feasible.
    For larger images, the gate count becomes very large.
    
    Args:
        image: 2D numpy array (uint8 grayscale)
        intensity_bits: number of bits for intensity (default 8)
    
    Returns:
        qc: QuantumCircuit with NEQR encoding
        n_pos_qubits: number of position qubits
        n_int_qubits: number of intensity qubits
    """
    h, w = image.shape
    n_pixels = h * w
    n_pos = int(np.ceil(np.log2(n_pixels)))
    n_int = intensity_bits
    total_qubits = n_pos + n_int
    
    # Ensure image is uint8
    img = image.astype(np.uint8)
    
    # Create circuit: [intensity_qubits | position_qubits]
    # Convention: intensity qubits are 0..n_int-1, position qubits are n_int..total-1
    qc = QuantumCircuit(total_qubits, name="NEQR")
    
    # Step 1: Create uniform superposition over positions
    for i in range(n_int, n_int + n_pos):
        qc.h(i)
    
    qc.barrier()
    
    # Step 2: For each pixel, apply multi-controlled X gates to set intensity bits
    flat = img.flatten()
    
    for pixel_idx in range(min(len(flat), 2 ** n_pos)):
        intensity = int(flat[pixel_idx])
        if intensity == 0:
            continue  # Skip zero-intensity pixels (already |0>)
        
        # Get binary representation of pixel position
        pos_bits = format(pixel_idx, f'0{n_pos}b')
        
        # Get binary representation of intensity
        int_bits = format(intensity, f'0{n_int}b')
        
        # For each intensity bit that is 1, apply multi-controlled X
        for bit_idx in range(n_int):
            if int_bits[n_int - 1 - bit_idx] == '1':
                # Target: intensity qubit bit_idx
                # Controls: all position qubits, matching the pixel position
                
                # First, flip position qubits where pos_bit is 0
                flips = []
                for p in range(n_pos):
                    if pos_bits[n_pos - 1 - p] == '0':
                        qc.x(n_int + p)
                        flips.append(n_int + p)
                
                # Multi-controlled X gate
                control_qubits = list(range(n_int, n_int + n_pos))
                target_qubit = bit_idx
                
                if len(control_qubits) == 1:
                    qc.cx(control_qubits[0], target_qubit)
                elif len(control_qubits) == 2:
                    qc.ccx(control_qubits[0], control_qubits[1], target_qubit)
                else:
                    qc.mcx(control_qubits, target_qubit)
                
                # Undo position flips
                for p in flips:
                    qc.x(p)
    
    return qc, n_pos, n_int


def neqr_encode_simplified(image, intensity_bits=4):
    """
    Simplified NEQR with reduced intensity bits for simulation feasibility.
    
    Using 4 bits (0-15 intensity levels) instead of 8 bits reduces qubit count.
    
    Args:
        image: 2D numpy array (uint8 grayscale)
        intensity_bits: reduced bit depth (default 4)
    
    Returns:
        qc, n_pos, n_int
    """
    # Reduce bit depth
    max_val = 2 ** intensity_bits - 1
    reduced = (image.astype(np.float64) / 255.0 * max_val).astype(np.uint8)
    
    return neqr_encode(reduced, intensity_bits)


def run_neqr_verify(image, intensity_bits=4, shots=8192):
    """
    Encode image with NEQR and verify by measuring in computational basis.
    
    Returns:
        reconstructed: reconstructed image from measurement results
    """
    h, w = image.shape
    n_pixels = h * w
    
    qc, n_pos, n_int = neqr_encode_simplified(image, intensity_bits)
    total = n_pos + n_int
    
    # Add measurements
    meas_qc = qc.copy()
    meas_qc.add_register(
        *[__import__('qiskit').circuit.ClassicalRegister(1) for _ in range(total)]
    ) if meas_qc.num_clbits == 0 else None
    
    # Simpler: create new circuit with classical bits
    full_qc = QuantumCircuit(total, total)
    full_qc.compose(qc, inplace=True)
    full_qc.measure(range(total), range(total))
    
    sim = AerSimulator()
    tc = transpile(full_qc, sim)
    result = sim.run(tc, shots=shots).result()
    counts = result.get_counts()
    
    # Reconstruct image from counts
    max_val = 2 ** n_int - 1
    reconstructed = np.zeros(2 ** n_pos)
    total_counts = np.zeros(2 ** n_pos)
    
    for bitstring, count in counts.items():
        bits = bitstring[::-1]  # Reverse for Qiskit ordering
        
        # Extract position and intensity
        if len(bits) >= total:
            int_bits = bits[:n_int]
            pos_bits = bits[n_int:n_int + n_pos]
            
            pos_idx = int(pos_bits, 2) if pos_bits else 0
            int_val = int(int_bits, 2) if int_bits else 0
            
            if pos_idx < len(reconstructed):
                reconstructed[pos_idx] += int_val * count
                total_counts[pos_idx] += count
    
    # Average intensity per position
    mask = total_counts > 0
    reconstructed[mask] /= total_counts[mask]
    
    # Scale back to 0-255
    reconstructed = (reconstructed / max(max_val, 1) * 255).astype(np.uint8)
    
    return reconstructed[:n_pixels].reshape(h, w), counts, full_qc


if __name__ == "__main__":
    from pathlib import Path
    from PIL import Image
    
    img = np.array(Image.open(
        Path(r"E:\projects\Quantum_Image\data\synthetic\images\circle_4x4.png")
    ))
    
    print(f"Testing NEQR on circle_4x4 (shape={img.shape})")
    print(f"Original:\n{img}")
    
    # Use 4-bit encoding for feasibility
    qc, n_pos, n_int = neqr_encode_simplified(img, intensity_bits=4)
    print(f"\nNEQR circuit: {qc.num_qubits} qubits (pos={n_pos}, int={n_int})")
    print(f"Circuit depth: {qc.depth()}")
    
    # Verify
    recon, counts, _ = run_neqr_verify(img, intensity_bits=4, shots=8192)
    print(f"\nReconstructed:\n{recon}")
    print(f"Reconstruction error (MAE): {np.mean(np.abs(img.astype(float) - recon.astype(float))):.2f}")
    print("NEQR encoder: OK")
