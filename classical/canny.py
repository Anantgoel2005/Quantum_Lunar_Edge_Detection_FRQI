"""
Classical Edge Detection - Canny Edge Detector

Multi-stage pipeline: Gaussian smoothing -> Sobel gradients ->
Non-maximum suppression -> Double threshold -> Hysteresis tracking.
"""
import numpy as np
import cv2


def canny_edge(image, low_threshold=50, high_threshold=150, aperture_size=3):
    """
    Apply Canny edge detection to a grayscale image.
    
    Args:
        image: 2D numpy array (uint8 grayscale)
        low_threshold: Lower threshold for hysteresis (0-255)
        high_threshold: Upper threshold for hysteresis (0-255)
        aperture_size: Sobel aperture size (3, 5, or 7)
    
    Returns:
        edges: 2D binary array (uint8, 0 or 255)
    """
    assert image.ndim == 2, f"Expected 2D grayscale, got shape {image.shape}"
    assert image.dtype == np.uint8, f"Expected uint8, got {image.dtype}"
    
    edges = cv2.Canny(image, low_threshold, high_threshold, apertureSize=aperture_size)
    return edges


def canny_edge_auto(image, sigma=0.33):
    """
    Apply Canny with automatic threshold selection based on image median.
    
    Uses the median of the pixel intensities to compute the thresholds:
        lower = max(0, (1 - sigma) * median)
        upper = min(255, (1 + sigma) * median)
    
    Args:
        image: 2D numpy array (uint8 grayscale)
        sigma: Threshold scaling factor (default 0.33)
    
    Returns:
        edges: 2D binary array (uint8, 0 or 255)
    """
    assert image.ndim == 2 and image.dtype == np.uint8
    
    median_val = np.median(image)
    low = int(max(0, (1.0 - sigma) * median_val))
    high = int(min(255, (1.0 + sigma) * median_val))
    
    # Ensure minimum separation
    if high - low < 20:
        low = max(0, int(median_val) - 20)
        high = min(255, int(median_val) + 20)
    
    return cv2.Canny(image, low, high)


if __name__ == "__main__":
    from pathlib import Path
    from PIL import Image
    
    test_img_path = Path(r"E:\projects\Quantum_Image\data\synthetic\images\circle_8x8.png")
    if test_img_path.exists():
        img = np.array(Image.open(test_img_path))
        edges = canny_edge(img)
        edges_auto = canny_edge_auto(img)
        print(f"Input shape: {img.shape}, range: [{img.min()}, {img.max()}]")
        print(f"Canny (fixed) edge pixels: {np.sum(edges > 0)}")
        print(f"Canny (auto) edge pixels: {np.sum(edges_auto > 0)}")
        print("Canny edge detection: OK")
