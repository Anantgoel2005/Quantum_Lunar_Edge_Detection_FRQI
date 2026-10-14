"""
Image Loader - Loads images from all dataset sources.

Supports:
  - Synthetic PNG images (8x8, 16x16)
  - SomBench WAC TIFF images (512x512, grayscale)
  - NASA LRO images (optional)
  - MNIST (debugging only)

All images returned as 2D numpy arrays (uint8 grayscale).
"""
import numpy as np
from pathlib import Path
from PIL import Image
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_synthetic(name, size):
    """
    Load a synthetic image and its ground truth mask.
    
    Args:
        name: geometry name (e.g., 'circle', 'horizontal_line')
        size: image size (4, 8, or 16)
    
    Returns:
        image: 2D uint8 array
        mask: 2D uint8 array (ground truth edges)
    """
    img_path = PROJECT_ROOT / "data" / "synthetic" / "images" / f"{name}_{size}x{size}.png"
    mask_path = PROJECT_ROOT / "data" / "synthetic" / "masks" / f"{name}_{size}x{size}_mask.png"
    
    assert img_path.exists(), f"Image not found: {img_path}"
    assert mask_path.exists(), f"Mask not found: {mask_path}"
    
    image = np.array(Image.open(img_path).convert("L"))
    mask = np.array(Image.open(mask_path).convert("L"))
    
    return image, mask


def load_all_synthetic(sizes=None):
    """
    Load all synthetic images and masks.
    
    Args:
        sizes: list of sizes to load (default: [8, 16])
    
    Returns:
        list of dicts: [{'name': str, 'size': int, 'image': ndarray, 'mask': ndarray}, ...]
    """
    if sizes is None:
        sizes = [8, 16]
    
    img_dir = PROJECT_ROOT / "data" / "synthetic" / "images"
    results = []
    
    for img_path in sorted(img_dir.glob("*.png")):
        parts = img_path.stem.rsplit("_", 1)  # e.g., ['circle', '8x8']
        if len(parts) != 2:
            continue
        name = parts[0]
        size_str = parts[1]  # '8x8' or '16x16'
        size = int(size_str.split("x")[0])
        
        if size not in sizes:
            continue
        
        mask_path = PROJECT_ROOT / "data" / "synthetic" / "masks" / f"{name}_{size_str}_mask.png"
        if not mask_path.exists():
            continue
        
        image = np.array(Image.open(img_path).convert("L"))
        mask = np.array(Image.open(mask_path).convert("L"))
        
        results.append({
            'name': name,
            'size': size,
            'image': image,
            'mask': mask,
            'source': 'synthetic',
        })
    
    return results


def load_sombench_tiff(filename):
    """
    Load a single SomBench WAC TIFF image as grayscale.
    
    Args:
        filename: TIFF filename (e.g., 'M1095814428CE_r1896_c752.tif')
    
    Returns:
        image: 2D uint8 array (512x512)
    """
    img_path = PROJECT_ROOT / "data" / "sombench" / "images" / filename
    assert img_path.exists(), f"Image not found: {img_path}"
    
    img = Image.open(img_path)
    
    # Handle multi-band TIFF — take first band if multi-band
    arr = np.array(img)
    if arr.ndim == 3:
        arr = arr[:, :, 0]
    
    # Normalize to uint8 if needed
    if arr.dtype != np.uint8:
        if arr.max() > 0:
            arr = ((arr - arr.min()) / (arr.max() - arr.min()) * 255).astype(np.uint8)
        else:
            arr = arr.astype(np.uint8)
    
    return arr


def load_sombench_metadata():
    """
    Load SomBench metadata with illumination angles etc.
    
    Returns:
        pandas DataFrame with columns: PRODUCT_ID, INCIDENCE_ANGLE, EMISSION_ANGLE, etc.
    """
    import pandas as pd
    meta_path = PROJECT_ROOT / "data" / "sombench" / "annotations" / "metadata.parquet"
    if meta_path.exists():
        return pd.read_parquet(meta_path)
    return None


def load_sombench_annotations(split="test"):
    """
    Load COCO-format annotations for SomBench WAC crater detection.
    
    Args:
        split: 'test' or 'val'
    
    Returns:
        dict with keys: 'images', 'annotations', 'categories'
    """
    ann_path = PROJECT_ROOT / "data" / "sombench" / "annotations" / f"{split}.json"
    assert ann_path.exists(), f"Annotations not found: {ann_path}"
    
    with open(ann_path, "r") as f:
        return json.load(f)


def list_available_sombench_images():
    """List all downloaded SomBench TIFF files."""
    img_dir = PROJECT_ROOT / "data" / "sombench" / "images"
    return sorted(img_dir.glob("*.tif"))


if __name__ == "__main__":
    print("=" * 60)
    print("Image Loader Test")
    print("=" * 60)
    
    # Test synthetic
    synth = load_all_synthetic()
    print(f"\nSynthetic images loaded: {len(synth)}")
    for s in synth[:3]:
        print(f"  {s['name']}_{s['size']}x{s['size']}: "
              f"shape={s['image'].shape}, mask_edges={np.sum(s['mask'] > 0)}")
    
    # Test SomBench
    tiff_files = list_available_sombench_images()
    print(f"\nSomBench TIFF files available: {len(tiff_files)}")
    if tiff_files:
        img = load_sombench_tiff(tiff_files[0].name)
        print(f"  First image: {tiff_files[0].name}, shape={img.shape}, "
              f"range=[{img.min()}, {img.max()}]")
    
    # Test annotations
    try:
        ann = load_sombench_annotations("test")
        print(f"\nTest annotations: {len(ann['images'])} images, "
              f"{len(ann['annotations'])} crater annotations")
    except Exception as e:
        print(f"\nAnnotations not yet available: {e}")
    
    print("\nImage loader: OK")
