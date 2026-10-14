"""
Annotation Rasteriser - Converts COCO polygons to pixel-level edge masks.

SomBench annotations are crater SEGMENTATION polygons (filled circles).
To get EDGE masks (crater rim only), we rasterise the polygon boundary.

Two output modes:
  1. Filled mask: the full filled crater region
  2. Rim mask: only the boundary pixels (what we need for edge detection)
"""
import numpy as np
import cv2
import json
from pathlib import Path


def polygon_to_filled_mask(segmentation, height=512, width=512):
    """
    Convert COCO segmentation polygon to a filled binary mask.
    
    Args:
        segmentation: list of polygon coordinates [[x1,y1,x2,y2,...], ...]
        height: image height
        width: image width
    
    Returns:
        mask: 2D uint8 array (0 or 255), filled polygon
    """
    mask = np.zeros((height, width), dtype=np.uint8)
    
    for polygon in segmentation:
        # Reshape flat list to Nx2 array
        pts = np.array(polygon, dtype=np.int32).reshape(-1, 2)
        cv2.fillPoly(mask, [pts], 255)
    
    return mask


def polygon_to_rim_mask(segmentation, height=512, width=512, rim_width=2):
    """
    Convert COCO segmentation polygon to a rim-only (boundary) mask.
    
    This is the ground truth for edge detection: only the boundary pixels
    of the crater, not the filled interior.
    
    Args:
        segmentation: list of polygon coordinates
        height: image height
        width: image width
        rim_width: thickness of the rim boundary in pixels
    
    Returns:
        rim_mask: 2D uint8 array (0 or 255), boundary only
    """
    mask = np.zeros((height, width), dtype=np.uint8)
    
    for polygon in segmentation:
        pts = np.array(polygon, dtype=np.int32).reshape(-1, 2)
        cv2.polylines(mask, [pts], isClosed=True, color=255, thickness=rim_width)
    
    return mask


def rasterise_image_annotations(annotations, image_id, height=512, width=512, 
                                  mode="rim", rim_width=2):
    """
    Rasterise all crater annotations for a given image.
    
    Args:
        annotations: list of COCO annotation dicts
        image_id: the image_id to filter by
        height: image height
        width: image width
        mode: 'rim' for boundary mask, 'filled' for interior mask
        rim_width: rim thickness (only for 'rim' mode)
    
    Returns:
        combined_mask: 2D uint8 array (0 or 255)
    """
    combined = np.zeros((height, width), dtype=np.uint8)
    
    image_anns = [a for a in annotations if a['image_id'] == image_id]
    
    for ann in image_anns:
        if 'segmentation' not in ann or not ann['segmentation']:
            continue
        
        if mode == "rim":
            mask = polygon_to_rim_mask(ann['segmentation'], height, width, rim_width)
        else:
            mask = polygon_to_filled_mask(ann['segmentation'], height, width)
        
        combined = np.maximum(combined, mask)
    
    return combined


def rasterise_all(split="test", mode="rim", rim_width=2):
    """
    Rasterise annotations for all images in a split and save as PNG masks.
    
    Args:
        split: 'test' or 'val'
        mode: 'rim' or 'filled'
        rim_width: rim thickness
    
    Returns:
        dict mapping image filename -> mask path
    """
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    ann_path = PROJECT_ROOT / "data" / "sombench" / "annotations" / f"{split}.json"
    masks_dir = PROJECT_ROOT / "data" / "sombench" / "masks"
    masks_dir.mkdir(parents=True, exist_ok=True)
    
    with open(ann_path) as f:
        data = json.load(f)
    
    images = data['images']
    annotations = data['annotations']
    
    results = {}
    for img_info in images:
        image_id = img_info['id']
        w = img_info.get('width', 512)
        h = img_info.get('height', 512)
        
        # Get filename stem (from .nc reference)
        stem = Path(img_info['file_name']).stem
        
        mask = rasterise_image_annotations(annotations, image_id, h, w, mode, rim_width)
        
        mask_filename = f"{stem}_{mode}_mask.png"
        mask_path = masks_dir / mask_filename
        
        from PIL import Image
        Image.fromarray(mask).save(mask_path)
        
        results[stem] = mask_path
        
        n_craters = len([a for a in annotations if a['image_id'] == image_id])
        n_edge_px = np.sum(mask > 0)
        
        if len(results) <= 5:
            print(f"  {stem}: {n_craters} craters, {n_edge_px} edge pixels")
    
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("Annotation Rasteriser - Creating Ground Truth Masks")
    print("=" * 60)
    
    for split in ["test", "val"]:
        ann_path = (Path(__file__).resolve().parents[1] / 'data/sombench/annotations') / f"{split}.json"
        if not ann_path.exists():
            print(f"\n  {split}.json not found - skipping")
            continue
        
        print(f"\n  Processing {split} split...")
        results = rasterise_all(split=split, mode="rim", rim_width=2)
        print(f"  Rasterised {len(results)} masks for {split} split")
    
    print("\n" + "=" * 60)
    print("Rasterisation complete!")
    print("=" * 60)
