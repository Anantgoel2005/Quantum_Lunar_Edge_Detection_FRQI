"""Matched classical controls for the hybrid NEQR reconstruction pipeline."""
import numpy as np


def forward_gradient(image):
    values = np.asarray(image, dtype=float)
    gx, gy = np.zeros_like(values), np.zeros_like(values)
    gx[:, 1:] = values[:, 1:] - values[:, :-1]
    gy[1:, :] = values[1:, :] - values[:-1, :]
    magnitude = np.hypot(gx, gy)
    return magnitude / magnitude.max() if magnitude.max() else magnitude


def quantized_gradient(image, intensity_bits=4):
    levels = 2 ** intensity_bits - 1
    quantized = np.floor(np.asarray(image, dtype=float) / 255 * levels)
    return forward_gradient(quantized)
