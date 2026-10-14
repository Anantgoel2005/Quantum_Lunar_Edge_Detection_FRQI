"""
Confidence Map Generator (Objective 22)

Produces pixel-level uncertainty maps from quantum measurement results.
Each pixel gets a mean probability and standard deviation across trials.

Output:
  - Mean edge probability map (0-1)
  - Standard deviation map (uncertainty width)
  - Visualizations: overlay of confidence on original image
"""
import numpy as np
import sys
from pathlib import Path
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from quantum.qhed_circuit import run_qhed_combined
from quantum.quantum_gradient import quantum_gradient_from_neqr

FIGURES_DIR = PROJECT_ROOT / "results" / "corrected" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def generate_confidence_maps(image, method="QPIE-QHED", n_trials=20, shots=8192):
    """
    Run multiple trials and produce mean + std confidence maps.
    
    Args:
        image: 2D uint8 array
        method: "QPIE-QHED" or "NEQR-Gradient"
        n_trials: number of repeated measurements
        shots: shots per trial
    
    Returns:
        mean_map: 2D float (mean edge probability per pixel)
        std_map: 2D float (uncertainty per pixel)
        all_maps: list of 2D arrays (individual trial results)
    """
    all_maps = []
    
    for t in range(n_trials):
        if method == "QPIE-QHED":
            combined, _, _ = run_qhed_combined(
                image.astype(np.float64), shots=shots, seed_simulator=42 + t
            )
            all_maps.append(combined)
        elif method == "NEQR-Gradient":
            edge_map, _, _ = quantum_gradient_from_neqr(
                image, intensity_bits=4, shots=shots, seed_simulator=42 + t
            )
            all_maps.append(edge_map)
    
    stack = np.stack(all_maps, axis=0)
    mean_map = np.mean(stack, axis=0)
    std_map = np.std(stack, axis=0)
    
    return mean_map, std_map, all_maps


def visualize_confidence(image, mean_map, std_map, method_name, image_name):
    """Create a 4-panel visualization of confidence maps."""
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    
    # Original image
    axes[0].imshow(image, cmap='gray', interpolation='nearest')
    axes[0].set_title('Original Image')
    axes[0].axis('off')
    
    # Mean edge probability
    im1 = axes[1].imshow(mean_map, cmap='hot', interpolation='nearest', vmin=0)
    axes[1].set_title('Mean Edge Probability')
    axes[1].axis('off')
    plt.colorbar(im1, ax=axes[1], fraction=0.046)
    
    # Uncertainty (std)
    im2 = axes[2].imshow(std_map, cmap='viridis', interpolation='nearest', vmin=0)
    axes[2].set_title('Uncertainty (Std Dev)')
    axes[2].axis('off')
    plt.colorbar(im2, ax=axes[2], fraction=0.046)
    
    # Coefficient of variation (relative uncertainty)
    with np.errstate(divide='ignore', invalid='ignore'):
        cv = np.where(mean_map > 0, std_map / mean_map, 0)
    im3 = axes[3].imshow(cv, cmap='plasma', interpolation='nearest', vmin=0, vmax=1)
    axes[3].set_title('Coeff. of Variation')
    axes[3].axis('off')
    plt.colorbar(im3, ax=axes[3], fraction=0.046)
    
    fig.suptitle(f'{method_name} -- {image_name}', fontsize=13)
    plt.tight_layout()
    
    fname = f"confidence_{method_name.lower().replace('-','_')}_{image_name}.png"
    fig.savefig(FIGURES_DIR / fname, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {fname}")


def main():
    print("=" * 60)
    print("CONFIDENCE MAP GENERATION")
    print("=" * 60)
    
    # Generate for two synthetic images
    for img_name in ["circle", "ellipse"]:
        img_path = PROJECT_ROOT / "data" / "synthetic" / "images" / f"{img_name}_8x8.png"
        if not img_path.exists():
            continue
        
        img = np.array(Image.open(img_path))
        print(f"\n  Image: {img_name}_8x8")
        
        for method in ["QPIE-QHED", "NEQR-Gradient"]:
            print(f"    Running {method} (20 trials)...")
            mean_map, std_map, _ = generate_confidence_maps(
                img, method=method, n_trials=20, shots=8192
            )
            
            print(f"      Mean edge prob range: [{mean_map.min():.4f}, {mean_map.max():.4f}]")
            print(f"      Max uncertainty: {std_map.max():.4f}")
            
            visualize_confidence(img, mean_map, std_map, method, img_name)
    
    print("\n" + "=" * 60)
    print("Confidence maps complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
