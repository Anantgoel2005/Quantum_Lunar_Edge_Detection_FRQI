"""
Preprocessor -- Image preprocessing strategies for Experiment 7.

Preprocessing options:
  None | Gaussian (sigma=1) | Median (3x3)
  CLAHE (clip=2, tile=4x4) | Histogram stretch | Gamma (0.5 and 1.5)
"""
import numpy as np
import cv2


def preprocess(image, method="none", **kwargs):
    """
    Apply a preprocessing method to a grayscale image.
    
    Args:
        image: 2D uint8 array
        method: preprocessing method name
    
    Returns:
        processed: 2D uint8 array
    """
    if method == "none":
        return image.copy()
    
    elif method == "gaussian":
        sigma = kwargs.get("sigma", 1.0)
        ksize = max(3, int(sigma * 4) | 1)  # Ensure odd
        return cv2.GaussianBlur(image, (ksize, ksize), sigma)
    
    elif method == "median":
        ksize = kwargs.get("ksize", 3)
        return cv2.medianBlur(image, ksize)
    
    elif method == "clahe":
        clip = kwargs.get("clip_limit", 2.0)
        tile = kwargs.get("tile_size", (4, 4))
        clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=tile)
        return clahe.apply(image)
    
    elif method == "histogram_stretch":
        p_low, p_high = np.percentile(image, [2, 98])
        if p_high > p_low:
            stretched = np.clip((image.astype(float) - p_low) / (p_high - p_low) * 255, 0, 255)
            return stretched.astype(np.uint8)
        return image.copy()
    
    elif method == "gamma":
        gamma = kwargs.get("gamma", 1.0)
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 
                         for i in range(256)]).astype(np.uint8)
        return cv2.LUT(image, table)
    
    else:
        raise ValueError(f"Unknown preprocessing method: {method}")


def get_preprocessing_configs():
    """Get all preprocessing configurations for Experiment 7."""
    return [
        ("none", {}),
        ("gaussian_s1", {"sigma": 1.0}),
        ("median_3x3", {"ksize": 3}),
        ("clahe", {"clip_limit": 2.0, "tile_size": (4, 4)}),
        ("hist_stretch", {}),
        ("gamma_0.5", {"gamma": 0.5}),
        ("gamma_1.5", {"gamma": 1.5}),
    ]
