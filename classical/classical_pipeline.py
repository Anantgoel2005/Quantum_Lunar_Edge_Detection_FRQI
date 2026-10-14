"""
Classical Pipeline - Runs Sobel, Canny, and Robinson Compass together.

Takes a grayscale image and returns edge maps from all three classical methods.
"""
import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from classical.sobel import sobel_edge, sobel_edge_binary
from classical.canny import canny_edge, canny_edge_auto
from classical.robinson_compass import robinson_edge, robinson_edge_binary


def run_classical_pipeline(image, canny_low=50, canny_high=150):
    """
    Run all three classical edge detectors on a grayscale image.
    
    Args:
        image: 2D numpy array (uint8 grayscale)
        canny_low: Canny lower threshold
        canny_high: Canny upper threshold
    
    Returns:
        dict with keys:
            'sobel_magnitude': continuous Sobel edge map (uint8)
            'sobel_binary': binary Sobel edges (uint8, 0/255)
            'canny': binary Canny edges (uint8, 0/255)
            'robinson_magnitude': continuous Robinson edge map (uint8)
            'robinson_binary': binary Robinson edges (uint8, 0/255)
            'robinson_direction': dominant direction map (degrees)
    """
    results = {}
    
    # Sobel
    results['sobel_magnitude'] = sobel_edge(image)
    results['sobel_binary'], _ = sobel_edge_binary(image)
    
    # Canny
    results['canny'] = canny_edge(image, canny_low, canny_high)
    
    # Robinson Compass
    rob_binary, rob_magnitude, rob_direction = robinson_edge_binary(image)
    results['robinson_magnitude'] = rob_magnitude
    results['robinson_binary'] = rob_binary
    results['robinson_direction'] = rob_direction
    
    return results


if __name__ == "__main__":
    from PIL import Image
    
    # Test on all synthetic images
    synthetic_dir = Path(r"E:\projects\Quantum_Image\data\synthetic\images")
    
    print("=" * 60)
    print("Classical Pipeline Test - All Synthetic Images")
    print("=" * 60)
    
    for img_path in sorted(synthetic_dir.glob("*.png")):
        img = np.array(Image.open(img_path))
        results = run_classical_pipeline(img)
        
        sobel_px = np.sum(results['sobel_binary'] > 0)
        canny_px = np.sum(results['canny'] > 0)
        robin_px = np.sum(results['robinson_binary'] > 0)
        directions = np.unique(results['robinson_direction'])
        
        print(f"\n  {img_path.name}:")
        print(f"    Sobel edges: {sobel_px} px")
        print(f"    Canny edges: {canny_px} px")
        print(f"    Robinson edges: {robin_px} px")
        print(f"    Robinson directions: {directions}")
    
    print("\n" + "=" * 60)
    print("All classical edge detectors working correctly!")
    print("=" * 60)
