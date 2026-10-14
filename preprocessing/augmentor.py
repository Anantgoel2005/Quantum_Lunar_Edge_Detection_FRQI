"""
Augmentor -- Image degradation for Experiment 4.

Degradation types:
  - Gaussian noise: sigma in {5, 10, 20, 30, 50}
  - Gaussian blur: sigma in {0, 0.5, 1.0, 1.5, 2.0}
  - Contrast scaling: factor in {0.25, 0.50, 0.75, 1.00, 1.25}
  - Illumination gradient: linear ramp, shadow regions
"""
import numpy as np
import cv2


def add_gaussian_noise(image, sigma=10):
    """Add Gaussian noise with given standard deviation."""
    noise = np.random.normal(0, sigma, image.shape)
    noisy = np.clip(image.astype(np.float64) + noise, 0, 255)
    return noisy.astype(np.uint8)


def add_gaussian_blur(image, sigma=1.0):
    """Apply Gaussian blur with given sigma."""
    if sigma <= 0:
        return image.copy()
    ksize = max(3, int(sigma * 4) | 1)
    return cv2.GaussianBlur(image, (ksize, ksize), sigma)


def scale_contrast(image, factor=1.0):
    """Scale contrast around the mean."""
    mean = np.mean(image)
    scaled = mean + (image.astype(np.float64) - mean) * factor
    return np.clip(scaled, 0, 255).astype(np.uint8)


def add_illumination_gradient(image, direction="horizontal", strength=0.3):
    """Add a linear illumination gradient."""
    h, w = image.shape
    if direction == "horizontal":
        ramp = np.linspace(1 - strength, 1 + strength, w)
        ramp = np.tile(ramp, (h, 1))
    else:
        ramp = np.linspace(1 - strength, 1 + strength, h)
        ramp = np.tile(ramp.reshape(-1, 1), (1, w))
    
    result = image.astype(np.float64) * ramp
    return np.clip(result, 0, 255).astype(np.uint8)


def add_shadow(image, shadow_factor=0.3):
    """Darken the right half of the image to simulate shadow."""
    result = image.copy().astype(np.float64)
    w = image.shape[1]
    result[:, w//2:] *= shadow_factor
    return np.clip(result, 0, 255).astype(np.uint8)


def get_degradation_configs():
    """Get all degradation configurations for Experiment 4."""
    configs = {
        "noise": [
            ("noise_5", {"sigma": 5}),
            ("noise_10", {"sigma": 10}),
            ("noise_20", {"sigma": 20}),
            ("noise_30", {"sigma": 30}),
            ("noise_50", {"sigma": 50}),
        ],
        "blur": [
            ("blur_0", {"sigma": 0}),
            ("blur_0.5", {"sigma": 0.5}),
            ("blur_1.0", {"sigma": 1.0}),
            ("blur_1.5", {"sigma": 1.5}),
            ("blur_2.0", {"sigma": 2.0}),
        ],
        "contrast": [
            ("contrast_0.25", {"factor": 0.25}),
            ("contrast_0.50", {"factor": 0.50}),
            ("contrast_0.75", {"factor": 0.75}),
            ("contrast_1.00", {"factor": 1.00}),
            ("contrast_1.25", {"factor": 1.25}),
        ],
        "illumination": [
            ("normal", {}),
            ("low_illum", {"factor": 0.3}),
            ("gradient", {"direction": "horizontal", "strength": 0.3}),
            ("shadow", {"shadow_factor": 0.3}),
        ],
    }
    return configs
