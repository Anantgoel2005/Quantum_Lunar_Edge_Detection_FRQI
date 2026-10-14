"""
Phase 1 - Step 1: Download SomBench WAC images and annotations.
Downloads the test split images (100 images) and annotation JSON.
Images are TIFF files, annotations are COCO format with segmentation polygons.

NOTE: Images in annotations reference .nc files but actual repo has .tif files.
We map between the two using the filename stem.
"""
import os
import sys
import json
import time
import numpy as np
from pathlib import Path
from tqdm import tqdm

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOMBENCH_DIR = PROJECT_ROOT / "data" / "sombench"
IMAGES_DIR = SOMBENCH_DIR / "images"
ANNOTATIONS_DIR = SOMBENCH_DIR / "annotations"
PATCHES_DIR = SOMBENCH_DIR / "patches"
MASKS_DIR = SOMBENCH_DIR / "masks"

for d in [IMAGES_DIR, ANNOTATIONS_DIR, PATCHES_DIR, MASKS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def download_annotations():
    """Download COCO JSON annotation files (test + val splits)."""
    from huggingface_hub import hf_hub_download
    
    repo_id = "nasa-ibm-ai4science/Sombench-WAC-Crater-Detection"
    
    for split in ["test", "val"]:
        out_path = ANNOTATIONS_DIR / f"{split}.json"
        if out_path.exists():
            print(f"  {split}.json already exists, skipping download")
            continue
        
        print(f"  Downloading {split}.json...")
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename=f"{split}.json",
            repo_type="dataset"
        )
        # Copy from HF cache to our project directory
        import shutil
        shutil.copy2(cached_path, out_path)
        print(f"  Saved to {out_path}")
    
    # Also download metadata
    meta_path = ANNOTATIONS_DIR / "metadata.parquet"
    if not meta_path.exists():
        print("  Downloading metadata.parquet...")
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename="metadata.parquet",
            repo_type="dataset"
        )
        import shutil
        shutil.copy2(cached_path, meta_path)
        print(f"  Saved to {meta_path}")


def download_images(max_images=None):
    """Download TIFF image files from the HuggingFace repo."""
    from huggingface_hub import hf_hub_download, list_repo_tree
    
    repo_id = "nasa-ibm-ai4science/Sombench-WAC-Crater-Detection"
    
    # Get list of all TIFF files
    print("  Listing image files...")
    items = list(list_repo_tree(repo_id, repo_type="dataset", path_in_repo="images_tiff"))
    tiff_files = [item for item in items if hasattr(item, "rfilename") and item.rfilename.endswith(".tif")]
    
    print(f"  Found {len(tiff_files)} TIFF files in repo")
    
    # Load test and val annotations to find which images we need
    test_images = set()
    val_images = set()
    
    for split, img_set in [("test", test_images), ("val", val_images)]:
        ann_path = ANNOTATIONS_DIR / f"{split}.json"
        if ann_path.exists():
            with open(ann_path) as f:
                data = json.load(f)
            for img in data["images"]:
                # Extract stem from .nc filename -> match to .tif
                stem = Path(img["file_name"]).stem  # e.g. M1174144247CE_r5360_c480
                img_set.add(stem)
    
    needed_stems = test_images | val_images
    print(f"  Need {len(needed_stems)} images (test={len(test_images)}, val={len(val_images)})")
    
    # Find matching TIFF files
    to_download = []
    for item in tiff_files:
        stem = Path(item.rfilename).stem
        if stem in needed_stems:
            to_download.append(item)
    
    print(f"  Matched {len(to_download)} TIFF files for test+val splits")
    
    if max_images:
        to_download = to_download[:max_images]
        print(f"  Limiting to {max_images} images")
    
    # Download each
    downloaded = 0
    failed = 0
    for item in tqdm(to_download, desc="  Downloading images"):
        out_path = IMAGES_DIR / Path(item.rfilename).name
        if out_path.exists():
            downloaded += 1
            continue
        
        try:
            cached_path = hf_hub_download(
                repo_id=repo_id,
                filename=item.rfilename,
                repo_type="dataset"
            )
            import shutil
            shutil.copy2(cached_path, out_path)
            downloaded += 1
        except Exception as e:
            print(f"\n  Failed to download {item.rfilename}: {e}")
            failed += 1
    
    print(f"  Downloaded: {downloaded}, Failed: {failed}")
    return downloaded


def verify_images():
    """Verify downloaded images can be opened and check their properties."""
    from PIL import Image
    import numpy as np
    
    tiff_files = sorted(IMAGES_DIR.glob("*.tif"))
    print(f"  Found {len(tiff_files)} TIFF files in {IMAGES_DIR}")
    
    if len(tiff_files) == 0:
        print("  WARNING: No TIFF files found!")
        return
    
    # Check first image
    img = Image.open(tiff_files[0])
    arr = np.array(img)
    print(f"  First image: {tiff_files[0].name}")
    print(f"    Size: {img.size}")
    print(f"    Mode: {img.mode}")
    print(f"    Array shape: {arr.shape}")
    print(f"    Dtype: {arr.dtype}")
    print(f"    Value range: [{arr.min()}, {arr.max()}]")
    print(f"    Mean: {arr.mean():.2f}")
    
    # Quick stats across all images
    widths = []
    heights = []
    for f in tiff_files[:20]:
        img = Image.open(f)
        widths.append(img.width)
        heights.append(img.height)
    
    print(f"  Image sizes (sample of {len(widths)}): {set(zip(widths, heights))}")


def main():
    print("=" * 60)
    print("PHASE 1 - Step 1: Download SomBench WAC Dataset")
    print("=" * 60)
    
    print("\n[1/3] Downloading annotation files...")
    download_annotations()
    
    print("\n[2/3] Downloading TIFF images (test + val splits)...")
    n_downloaded = download_images()
    
    print("\n[3/3] Verifying downloaded images...")
    verify_images()
    
    print("\n" + "=" * 60)
    print("Download complete!")
    print(f"  Annotations: {ANNOTATIONS_DIR}")
    print(f"  Images: {IMAGES_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
