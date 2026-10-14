"""
Phase 1 - Synthetic Ground Truth Generator

Generates synthetic grayscale images with known exact edge positions.
Each image comes with an analytically computed binary edge mask.

Geometry types:
  1. Horizontal line
  2. Vertical line
  3. 45-degree diagonal
  4. Corner junction
  5. Circle (r=3)
  6. Ellipse (a=3, b=2)
  7. Multiple circles
  8. Irregular curved boundary

Output sizes: 8x8 and 16x16 patches (primary experiment sizes)
All images saved as uint8 grayscale PNG files.
"""
import numpy as np
from PIL import Image
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"
IMAGES_DIR = SYNTHETIC_DIR / "images"
MASKS_DIR = SYNTHETIC_DIR / "masks"

for d in [IMAGES_DIR, MASKS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def save_pair(name, image_arr, mask_arr, size):
    """Save an image-mask pair as PNG files."""
    assert image_arr.shape == (size, size), f"Image shape mismatch: {image_arr.shape}"
    assert mask_arr.shape == (size, size), f"Mask shape mismatch: {mask_arr.shape}"
    assert image_arr.dtype == np.uint8
    assert mask_arr.dtype == np.uint8
    
    img = Image.fromarray(image_arr, mode="L")
    mask = Image.fromarray(mask_arr, mode="L")
    
    img.save(IMAGES_DIR / f"{name}_{size}x{size}.png")
    mask.save(MASKS_DIR / f"{name}_{size}x{size}_mask.png")


def horizontal_line(size):
    """Dark background with a bright horizontal band at the centre."""
    img = np.full((size, size), 30, dtype=np.uint8)  # dark bg
    mid = size // 2
    img[mid, :] = 200  # bright line
    if size >= 16:
        img[mid - 1, :] = 200
    
    # Edge mask: edges are at the boundaries of the line
    mask = np.zeros((size, size), dtype=np.uint8)
    mask[mid - 1, :] = 255  # top edge of line
    if size >= 16:
        mask[mid - 2, :] = 255
        mask[mid, :] = 255   # bottom edge of line
    else:
        mask[mid + 1, :] = 255
    return img, mask


def vertical_line(size):
    """Dark background with a bright vertical band at the centre."""
    img = np.full((size, size), 30, dtype=np.uint8)
    mid = size // 2
    img[:, mid] = 200
    if size >= 16:
        img[:, mid - 1] = 200
    
    mask = np.zeros((size, size), dtype=np.uint8)
    mask[:, mid - 1] = 255
    if size >= 16:
        mask[:, mid - 2] = 255
        mask[:, mid] = 255
    else:
        mask[:, mid + 1] = 255
    return img, mask


def diagonal_45(size):
    """Dark background with a bright 45-degree diagonal."""
    img = np.full((size, size), 30, dtype=np.uint8)
    mask = np.zeros((size, size), dtype=np.uint8)
    
    for i in range(size):
        if 0 <= i < size:
            img[i, i] = 200
            # Edges are adjacent pixels
            if i - 1 >= 0 and i + 1 < size:
                mask[i - 1, i] = 255  # above
                mask[i, i - 1] = 255  # left
                mask[i + 1, i] = 255  # below
                mask[i, i + 1] = 255  # right
    
    return img, mask


def corner_junction(size):
    """Dark background with a bright L-shaped corner (bottom-left quadrant bright)."""
    img = np.full((size, size), 30, dtype=np.uint8)
    mid = size // 2
    img[mid:, :mid] = 200  # bottom-left quadrant bright
    
    # Edge mask: the L-shaped boundary
    mask = np.zeros((size, size), dtype=np.uint8)
    # Horizontal boundary at row=mid
    mask[mid, :mid] = 255
    if mid > 0:
        mask[mid - 1, :mid] = 255
    # Vertical boundary at col=mid
    mask[mid:, mid] = 255
    mask[mid:, mid - 1] = 255
    
    return img, mask


def circle(size, radius=None):
    """Dark background with a bright filled circle at the centre."""
    if radius is None:
        radius = size // 4 + 1  # r=3 for 8x8, r=5 for 16x16
    
    img = np.full((size, size), 30, dtype=np.uint8)
    mask = np.zeros((size, size), dtype=np.uint8)
    
    cy, cx = size / 2.0 - 0.5, size / 2.0 - 0.5
    
    for y in range(size):
        for x in range(size):
            dist = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)
            if dist <= radius:
                img[y, x] = 200
            
            # Edge: pixel is on boundary if it's inside but has a neighbour outside
            # or outside but has a neighbour inside
            if abs(dist - radius) <= 1.2:
                mask[y, x] = 255
    
    return img, mask


def ellipse(size, a=None, b=None):
    """Dark background with a bright filled ellipse."""
    if a is None:
        a = size // 4 + 1  # semi-major
    if b is None:
        b = max(size // 6, 2)  # semi-minor
    
    img = np.full((size, size), 30, dtype=np.uint8)
    mask = np.zeros((size, size), dtype=np.uint8)
    
    cy, cx = size / 2.0 - 0.5, size / 2.0 - 0.5
    
    for y in range(size):
        for x in range(size):
            val = ((y - cy) / b) ** 2 + ((x - cx) / a) ** 2
            if val <= 1.0:
                img[y, x] = 200
            
            if abs(val - 1.0) <= 0.6:
                mask[y, x] = 255
    
    return img, mask


def multiple_circles(size):
    """Dark background with two or three bright circles at different positions."""
    img = np.full((size, size), 30, dtype=np.uint8)
    mask = np.zeros((size, size), dtype=np.uint8)
    
    if size == 8:
        circles_params = [
            (2, 2, 1.5),   # (cy, cx, r)
            (5, 5, 1.5),
        ]
    else:  # 16x16
        circles_params = [
            (4, 4, 2.5),
            (11, 11, 2.5),
            (4, 11, 1.8),
        ]
    
    for cy, cx, r in circles_params:
        for y in range(size):
            for x in range(size):
                dist = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)
                if dist <= r:
                    img[y, x] = 200
                if abs(dist - r) <= 1.2:
                    mask[y, x] = 255
    
    return img, mask


def irregular_curve(size):
    """Dark background with an irregular curved boundary (sine-wave edge)."""
    img = np.full((size, size), 30, dtype=np.uint8)
    mask = np.zeros((size, size), dtype=np.uint8)
    
    for x in range(size):
        # Sine wave boundary
        boundary_y = size / 2.0 + (size / 6.0) * np.sin(2 * np.pi * x / size)
        
        for y in range(size):
            if y >= boundary_y:
                img[y, x] = 200
            
            # Edge: pixels near the boundary
            if abs(y - boundary_y) <= 1.0:
                mask[y, x] = 255
    
    return img, mask


def generate_all():
    """Generate all synthetic images and masks at both resolutions."""
    generators = {
        "horizontal_line": horizontal_line,
        "vertical_line": vertical_line,
        "diagonal_45": diagonal_45,
        "corner_junction": corner_junction,
        "circle": circle,
        "ellipse": ellipse,
        "multiple_circles": multiple_circles,
        "irregular_curve": irregular_curve,
    }
    
    sizes = [8, 16]
    total = 0
    
    for name, gen_func in generators.items():
        for size in sizes:
            img, mask = gen_func(size)
            save_pair(name, img, mask, size)
            total += 1
            print(f"  Generated: {name}_{size}x{size} "
                  f"(img range: [{img.min()}-{img.max()}], "
                  f"mask edge pixels: {np.sum(mask > 0)})")
    
    # Also generate a 4x4 circle for QPIE validation (5 qubits)
    img_4, mask_4 = circle(4, radius=1.5)
    save_pair("circle", img_4, mask_4, 4)
    total += 1
    print(f"  Generated: circle_4x4 (validation image)")
    
    return total


def main():
    print("=" * 60)
    print("PHASE 1 - Synthetic Ground Truth Generator")
    print("=" * 60)
    
    n = generate_all()
    
    print(f"\nGenerated {n} image-mask pairs")
    print(f"  Images: {IMAGES_DIR}")
    print(f"  Masks:  {MASKS_DIR}")
    
    # List generated files
    img_files = sorted(IMAGES_DIR.glob("*.png"))
    mask_files = sorted(MASKS_DIR.glob("*.png"))
    print(f"\n  Image files: {len(img_files)}")
    for f in img_files:
        print(f"    {f.name}")
    print(f"\n  Mask files: {len(mask_files)}")
    for f in mask_files:
        print(f"    {f.name}")
    
    print("\n" + "=" * 60)
    print("Synthetic dataset generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
