"""QPIE/Hadamard edges with two pair offsets in each direction.

Offset 0 covers (0,1), (2,3), ... . Offset 1 increments the coordinate
register before H, covering (1,2), (3,4), ... . Wraparound pairs are
excluded. Edges are placed at the right/bottom pixel. No ancilla is used.
"""
import numpy as np
from qiskit import QuantumCircuit
from quantum.simulation import validate_image, simulate_counts


def build_qhed_circuit(image, direction="horizontal", pair_offset=0):
    image = validate_image(image, power_of_two=True)
    if direction not in ("horizontal", "vertical"):
        raise ValueError("direction must be horizontal or vertical")
    if pair_offset not in (0, 1):
        raise ValueError("pair_offset must be 0 or 1")
    height, width = image.shape
    col_bits, row_bits = width.bit_length() - 1, height.bit_length() - 1
    selected = list(range(col_bits)) if direction == "horizontal" else list(range(col_bits, col_bits + row_bits))
    if not selected:
        raise ValueError("Selected direction requires at least two pixels")
    n_qubits = col_bits + row_bits
    flat = image.flatten().astype(float)
    norm = np.linalg.norm(flat)
    amplitudes = flat / norm if norm else np.full(image.size, 1 / np.sqrt(image.size))
    qc = QuantumCircuit(n_qubits, n_qubits, name=f"QHED_{direction}_{pair_offset}")
    qc.initialize(amplitudes, range(n_qubits))
    qc.barrier()
    if pair_offset:
        # Modular increment: test lower bits before modifying them.
        for index in range(len(selected) - 1, 0, -1):
            controls = selected[:index]
            if len(controls) == 1:
                qc.cx(controls[0], selected[index])
            else:
                qc.mcx(controls, selected[index])
        qc.x(selected[0])
        qc.barrier()
    qc.h(selected[0])
    qc.barrier()
    qc.measure(range(n_qubits), range(n_qubits))
    qc.metadata = {"direction": direction, "pair_offset": pair_offset, "image_shape": list(image.shape)}
    return qc, n_qubits, selected[0]


def qhed_counts_to_edge_map(counts, image_shape, direction, pair_offset=0):
    height, width = image_shape
    stride = 1 if direction == "horizontal" else width
    length = width if direction == "horizontal" else height
    result = np.zeros(height * width)
    total = sum(counts.values())
    if total == 0:
        return result.reshape(image_shape)
    for bitstring, count in counts.items():
        value = int(bitstring.replace(" ", ""), 2)
        if value & stride:
            base = value & ~stride
            coordinate = base % width if direction == "horizontal" else base // width
            destination = (coordinate + 1 - pair_offset) % length
            if destination == 0:
                continue  # circular pairs are not image neighbors
            pixel = base + (destination - coordinate) * stride
            result[pixel] += count / total
    return result.reshape(image_shape)


def run_qhed(image, shots=8192, direction="horizontal", noise_model=None,
             pair_offset=0, seed_simulator=None):
    """Execute one directional pair pass; return map, counts and circuit."""
    image = np.asarray(image)
    qc, _, _ = build_qhed_circuit(image, direction, pair_offset)
    counts = simulate_counts(qc, shots, noise_model, seed_simulator)
    return qhed_counts_to_edge_map(counts, image.shape, direction, pair_offset), counts, qc


def run_qhed_combined(image, shots=8192, noise_model=None, seed_simulator=None):
    """Four independent circuits, each with `shots` samples (4*shots total)."""
    image = validate_image(image, power_of_two=True)
    maps = []
    for direction, length in [("horizontal", image.shape[1]), ("vertical", image.shape[0])]:
        passes = []
        for offset in (0, 1):
            if length < 2:
                passes.append(np.zeros_like(image, dtype=float))
                continue
            seed = None if seed_simulator is None else seed_simulator + 2 * len(maps) + offset
            edge, _, _ = run_qhed(image, shots, direction, noise_model, offset, seed)
            passes.append(edge)
        maps.append(np.maximum(*passes))
    return np.maximum(*maps), maps[0], maps[1]
