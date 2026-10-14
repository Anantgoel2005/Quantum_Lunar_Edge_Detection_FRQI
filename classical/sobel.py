"""
Classical Edge Detection - Sobel Filter

Applies Sobel gradient filter to grayscale images.
Returns edge magnitude map (uint8) and optional thresholded binary edge map.
"""
import numpy as np
import cv2


def sobel_edge(image, ksize=3, normalize=True):
    """
    Apply Sobel edge detection to a grayscale image.
    
    Args:
        image: 2D numpy array (uint8 grayscale)
        ksize: Sobel kernel size (default 3)
        normalize: If True, normalize output to [0, 255] uint8
    
    Returns:
        edge_magnitude: 2D array of edge strength (uint8 if normalized)
    """
    assert image.ndim == 2, f"Expected 2D grayscale, got shape {image.shape}"
    
    # Convert to float for computation
    img_float = image.astype(np.float64)
    
    # Compute gradients
    gx = cv2.Sobel(img_float, cv2.CV_64F, 1, 0, ksize=ksize)
    gy = cv2.Sobel(img_float, cv2.CV_64F, 0, 1, ksize=ksize)
    
    # Edge magnitude
    magnitude = np.sqrt(gx ** 2 + gy ** 2)
    
    if normalize:
        # Normalize to 0-255
        if magnitude.max() > 0:
            magnitude = (magnitude / magnitude.max() * 255).astype(np.uint8)
        else:
            magnitude = magnitude.astype(np.uint8)
    
    return magnitude


def sobel_edge_binary(image, ksize=3, threshold=None):
    """
    Apply Sobel and threshold to produce binary edge map.
    
    Args:
        image: 2D numpy array (uint8 grayscale)
        ksize: Sobel kernel size
        threshold: If None, uses Otsu's method. Otherwise fixed threshold (0-255).
    
    Returns:
        binary_edges: 2D binary array (uint8, 0 or 255)
        magnitude: continuous edge magnitude map
    """
    magnitude = sobel_edge(image, ksize=ksize, normalize=True)
    
    if threshold is None:
        # Use Otsu's thresholding
        _, binary = cv2.threshold(magnitude, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        _, binary = cv2.threshold(magnitude, threshold, 255, cv2.THRESH_BINARY)
    
    return binary, magnitude


if __name__ == "__main__":
    # Quick test on a synthetic image
    from pathlib import Path
    from PIL import Image
    
    test_img_path = (Path(__file__).resolve().parents[1] / 'data/synthetic/images/circle_8x8.png')
    if test_img_path.exists():
        img = np.array(Image.open(test_img_path))
        magnitude = sobel_edge(img)
        binary, _ = sobel_edge_binary(img)
        print(f"Input shape: {img.shape}, range: [{img.min()}, {img.max()}]")
        print(f"Sobel magnitude range: [{magnitude.min()}, {magnitude.max()}]")
        print(f"Binary edge pixels: {np.sum(binary > 0)}")
        print("Sobel edge detection: OK")
    else:
        print(f"Test image not found: {test_img_path}")
