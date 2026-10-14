"""ANALYTICAL REFERENCE ONLY: ideal probabilities and correctness checks.

This uses exact Born probabilities and multinomial shot sampling, avoiding
gate compilation for thousands of ideal circuits. It is not a QPU backend.
Small patches can be cross-checked with the Qiskit implementation.
The automatic real-case inference path is quantum/full_image.py and does not
call this module. Use that path for actual circuit-based edge detection.
"""
import numpy as np
from quantum.simulation import validate_image


def qhed_patch_probabilities(image, direction, pair_offset):
    image = validate_image(image, power_of_two=True).astype(float)
    if direction not in ('horizontal', 'vertical') or pair_offset not in (0, 1):
        raise ValueError('Invalid direction or pair offset')
    axis = 1 if direction == 'horizontal' else 0
    if image.shape[axis] < 2:
        raise ValueError('Selected axis requires at least two pixels')
    norm_squared = float(np.sum(image * image))
    amplitudes = image / np.sqrt(norm_squared) if norm_squared else np.full(image.shape, 1 / np.sqrt(image.size))
    amplitudes = np.roll(amplitudes, pair_offset, axis=axis)
    paired = np.moveaxis(amplitudes, axis, -1).copy()
    even, odd = paired[..., ::2].copy(), paired[..., 1::2].copy()
    paired[..., ::2] = (even + odd) / np.sqrt(2)
    paired[..., 1::2] = (even - odd) / np.sqrt(2)
    state = np.moveaxis(paired, -1, axis)
    return state * state, norm_squared


def qhed_patch(image, shots=None, seed=42):
    """Return H/V squared intensity differences and raw accepted probabilities."""
    image = validate_image(image, power_of_two=True)
    if shots is not None and (not isinstance(shots, (int, np.integer)) or shots <= 0):
        raise ValueError('shots must be a positive integer or None for exact mode')
    rng = np.random.default_rng(seed)
    squared_maps, probability_maps, observed = [], [], 0
    for direction in ('horizontal', 'vertical'):
        axis = 1 if direction == 'horizontal' else 0
        directional = np.zeros_like(image, dtype=float)
        raw = np.zeros_like(image, dtype=float)
        for offset in (0, 1):
            probabilities, norm = qhed_patch_probabilities(image, direction, offset)
            if shots is not None:
                flat = probabilities.ravel().copy()
                flat /= flat.sum()
                probabilities = rng.multinomial(int(shots), flat).reshape(image.shape) / shots
            # Odd coordinate outcomes encode differences; anchor at right/bottom.
            edges = np.zeros_like(probabilities)
            if axis == 1:
                edges[:, 1::2] = probabilities[:, 1::2]
            else:
                edges[1::2, :] = probabilities[1::2, :]
            edges = np.roll(edges, -offset, axis=axis)
            if axis == 1:
                edges[:, 0] = 0
            else:
                edges[0, :] = 0
            directional = np.maximum(directional, 2 * norm * edges)
            raw = np.maximum(raw, edges)
        squared_maps.append(directional)
        probability_maps.append(raw)
        if shots is not None:
            observed += int(np.count_nonzero(raw))
    return squared_maps, probability_maps, observed


def neqr_patch(image, intensity_bits=4, shots=None, seed=42):
    image = validate_image(image, power_of_two=True)
    if not isinstance(intensity_bits, int) or not 1 <= intensity_bits <= 8 or np.any(image > 255):
        raise ValueError('Expected 1-8 intensity bits and pixel intensities in 0-255')
    if shots is not None and (not isinstance(shots, (int, np.integer)) or shots <= 0):
        raise ValueError('shots must be positive')
    levels = (1 << intensity_bits) - 1
    values = np.floor(image.astype(float) / 255 * levels) / levels * 255
    if shots is None:
        coverage = np.ones_like(values, dtype=bool)
    else:
        counts = np.random.default_rng(seed).multinomial(int(shots), np.full(image.size, 1 / image.size))
        coverage = counts.reshape(image.shape) > 0
    return np.where(coverage, values, 0), coverage


def tiled_quantum_edges(image, tile_size=16, shots=8192, seed=42):
    """Haloed tiles preserve native-resolution neighbors; each core is used once.

    QHED probabilities are converted to squared physical intensity differences
    with their known preparation norm before stitching. Normalization happens
    once for each full image, avoiding per-tile brightness seams.
    """
    image = validate_image(image)
    if np.any(image > 255):
        raise ValueError('Expected an image scaled to 0-255')
    if not isinstance(tile_size, int) or tile_size < 4 or tile_size & (tile_size - 1):
        raise ValueError('tile_size must be a power of two of at least 4')
    height, width = image.shape
    core = tile_size - 2
    padded = np.pad(image, ((1, tile_size), (1, tile_size)), mode='edge')
    output = {name: np.zeros_like(image, dtype=float) for name in ['qhed_exact','qhed_sampled','neqr_exact','neqr_sampled']}
    neqr_coverage = np.zeros_like(image, dtype=bool)
    tile_count = 0
    for y in range(0, height, core):
        for x in range(0, width, core):
            patch = padded[y:y+tile_size, x:x+tile_size]
            block_height, block_width = min(core,height-y), min(core,width-x)
            crop = np.s_[1:1+block_height, 1:1+block_width]
            target = np.s_[y:y+block_height, x:x+block_width]
            tile_seed = int(np.random.SeedSequence([seed,tile_count]).generate_state(1)[0])
            for name, budget in [('qhed_exact',None),('qhed_sampled',shots)]:
                (h2,v2), _, _ = qhed_patch(patch, shots=budget, seed=tile_seed)
                if x == 0: h2[:,1] = 0
                if y == 0: v2[1,:] = 0
                output[name][target] = np.sqrt(h2[crop]+v2[crop])
            for name, budget in [('neqr_exact',None),('neqr_sampled',shots)]:
                reconstructed, coverage = neqr_patch(patch, shots=budget, seed=tile_seed)
                gx, gy = np.zeros_like(reconstructed), np.zeros_like(reconstructed)
                gx[:,1:] = np.diff(reconstructed, axis=1)
                gy[1:,:] = np.diff(reconstructed, axis=0)
                if x == 0: gx[:,1] = 0
                if y == 0: gy[1,:] = 0
                output[name][target] = np.hypot(gx[crop],gy[crop])
                if budget is not None: neqr_coverage[target] = coverage[crop]
            tile_count += 1
    for name, values in output.items():
        if values.max() > 0:
            output[name] = values / values.max()
    return output, {'tile_size':tile_size,'core_size':core,'tiles':tile_count,
        'shots_per_circuit':shots,'qhed_circuits':tile_count*4,'neqr_circuits':tile_count,
        'qhed_total_shots':tile_count*4*shots,'neqr_total_shots':tile_count*shots,
        'neqr_position_coverage':float(neqr_coverage.mean()), 'seed':seed,
        'backend':'ideal Born-probability simulator; not gate-level execution'}
