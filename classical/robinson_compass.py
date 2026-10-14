"""
Classical Edge Detection - Robinson Compass Operator (Robinson, 1977)

A directional edge detector using eight 3x3 masks corresponding to
the eight compass directions (0, 45, 90, 135, 180, 225, 270, 315 degrees).

Edge strength: E(x,y) = max_k |R_k(x,y)|
Dominant direction: D(x,y) = argmax_k |R_k(x,y)|  (in degrees)

This provides a direction-aware classical reference for Experiment 6
(geometry ablation), enabling diagnosis of whether quantum edge
detection failures are direction-specific or image-level.
"""
import numpy as np
import cv2


# Robinson compass masks — 8 directions
# Each mask is a 3x3 kernel for a specific compass direction
ROBINSON_MASKS = {
    0: np.array([      # East (horizontal edge response)
        [-1,  0,  1],
        [-2,  0,  2],
        [-1,  0,  1]
    ], dtype=np.float64),
    
    45: np.array([     # North-East (45-degree diagonal response)
        [ 0,  1,  2],
        [-1,  0,  1],
        [-2, -1,  0]
    ], dtype=np.float64),
    
    90: np.array([     # North (vertical edge response)
        [ 1,  2,  1],
        [ 0,  0,  0],
        [-1, -2, -1]
    ], dtype=np.float64),
    
    135: np.array([    # North-West (135-degree diagonal response)
        [ 2,  1,  0],
        [ 1,  0, -1],
        [ 0, -1, -2]
    ], dtype=np.float64),
    
    180: np.array([    # West (horizontal edge response, opposite)
        [ 1,  0, -1],
        [ 2,  0, -2],
        [ 1,  0, -1]
    ], dtype=np.float64),
    
    225: np.array([    # South-West
        [ 0, -1, -2],
        [ 1,  0, -1],
        [ 2,  1,  0]
    ], dtype=np.float64),
    
    270: np.array([    # South (vertical edge response, opposite)
        [-1, -2, -1],
        [ 0,  0,  0],
        [ 1,  2,  1]
    ], dtype=np.float64),
    
    315: np.array([    # South-East
        [-2, -1,  0],
        [-1,  0,  1],
        [ 0,  1,  2]
    ], dtype=np.float64),
}

DIRECTION_ANGLES = sorted(ROBINSON_MASKS.keys())  # [0, 45, 90, ..., 315]


def robinson_edge(image):
    """
    Apply Robinson Compass edge detection.
    
    Args:
        image: 2D numpy array (uint8 grayscale)
    
    Returns:
        edge_magnitude: 2D array (uint8, 0-255) — max response across all 8 directions
        dominant_direction: 2D array (int) — dominant direction in degrees (0-315)
        directional_responses: dict mapping angle -> 2D response array (float64)
    """
    assert image.ndim == 2, f"Expected 2D grayscale, got shape {image.shape}"
    
    img_float = image.astype(np.float64)
    
    # Compute response for each compass direction
    directional_responses = {}
    for angle in DIRECTION_ANGLES:
        mask = ROBINSON_MASKS[angle]
        response = cv2.filter2D(img_float, cv2.CV_64F, mask)
        directional_responses[angle] = response
    
    # Stack responses: shape (8, H, W)
    responses_stack = np.stack(
        [np.abs(directional_responses[a]) for a in DIRECTION_ANGLES],
        axis=0
    )
    
    # Edge magnitude: max over all directions
    magnitude_float = np.max(responses_stack, axis=0)
    
    # Dominant direction: argmax over directions
    argmax_idx = np.argmax(responses_stack, axis=0)
    dominant_direction = np.array(DIRECTION_ANGLES)[argmax_idx]
    
    # Normalize magnitude to 0-255 uint8
    if magnitude_float.max() > 0:
        edge_magnitude = (magnitude_float / magnitude_float.max() * 255).astype(np.uint8)
    else:
        edge_magnitude = np.zeros_like(image, dtype=np.uint8)
    
    return edge_magnitude, dominant_direction, directional_responses


def robinson_edge_binary(image, threshold=None):
    """
    Robinson edge detection with binary thresholding.
    
    Args:
        image: 2D numpy array (uint8 grayscale)
        threshold: Fixed threshold (0-255) or None for Otsu
    
    Returns:
        binary_edges: 2D binary array (uint8, 0 or 255)
        edge_magnitude: continuous magnitude map
        dominant_direction: direction map in degrees
    """
    edge_magnitude, dominant_direction, _ = robinson_edge(image)
    
    if threshold is None:
        _, binary = cv2.threshold(edge_magnitude, 0, 255, 
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        _, binary = cv2.threshold(edge_magnitude, threshold, 255, 
                                  cv2.THRESH_BINARY)
    
    return binary, edge_magnitude, dominant_direction


def robinson_directional_strength(image, target_angle):
    """
    Get the Robinson response for a single specific compass direction.
    
    Useful for analyzing whether a specific edge orientation is present.
    
    Args:
        image: 2D numpy array (uint8)
        target_angle: One of [0, 45, 90, 135, 180, 225, 270, 315]
    
    Returns:
        response: 2D float64 array (signed response for that direction)
    """
    assert target_angle in ROBINSON_MASKS, f"Invalid angle {target_angle}"
    
    img_float = image.astype(np.float64)
    mask = ROBINSON_MASKS[target_angle]
    return cv2.filter2D(img_float, cv2.CV_64F, mask)


if __name__ == "__main__":
    from pathlib import Path
    from PIL import Image
    
    test_img_path = Path(r"E:\projects\Quantum_Image\data\synthetic\images\circle_8x8.png")
    if test_img_path.exists():
        img = np.array(Image.open(test_img_path))
        magnitude, direction, responses = robinson_edge(img)
        binary, _, _ = robinson_edge_binary(img)
        
        print(f"Input shape: {img.shape}, range: [{img.min()}, {img.max()}]")
        print(f"Robinson magnitude range: [{magnitude.min()}, {magnitude.max()}]")
        print(f"Binary edge pixels: {np.sum(binary > 0)}")
        print(f"Dominant directions present: {np.unique(direction)}")
        
        # Show per-direction peak response
        for angle in DIRECTION_ANGLES:
            peak = np.max(np.abs(responses[angle]))
            print(f"  {angle:3d} deg: peak response = {peak:.1f}")
        
        print("Robinson compass edge detection: OK")
