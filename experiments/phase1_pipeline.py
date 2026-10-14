"""
Phase 1 - Complete Pipeline: Dataset Curation, Patch Extraction, and Classical Evaluation

This script:
1. Loads all 200 SomBench images (test + val splits)
2. Analyses each for contrast, illumination, crater characteristics  
3. Performs stratified sampling to select 30 representative patches
4. Extracts 8x8 and 16x16 patches centered on craters
5. Rasterises COCO annotations to pixel-level rim masks
6. Runs Sobel, Canny, Robinson on all 30 patches
7. Evaluates against ground truth and stores results

This is the MASTER script for Phase 1 of the project.
"""
import numpy as np
import json
import csv
import sys
from pathlib import Path
from PIL import Image
import cv2
import tifffile

# Project paths
PROJECT_ROOT = Path(r"E:\projects\Quantum_Image")
SOMBENCH_DIR = PROJECT_ROOT / "data" / "sombench"
IMAGES_DIR = SOMBENCH_DIR / "images"
ANNOTATIONS_DIR = SOMBENCH_DIR / "annotations"
PATCHES_DIR = SOMBENCH_DIR / "patches"
MASKS_DIR = SOMBENCH_DIR / "masks"
RESULTS_DIR = PROJECT_ROOT / "results"

sys.path.insert(0, str(PROJECT_ROOT))

from classical.sobel import sobel_edge, sobel_edge_binary
from classical.canny import canny_edge_auto
from classical.robinson_compass import robinson_edge, robinson_edge_binary
from evaluation.metrics import compute_all_metrics, print_metrics


# ============================================================
# STEP 1: Load and characterise all SomBench images
# ============================================================

def load_sombench_image(tif_path):
    """Load a SomBench GeoTIFF and return grayscale uint8."""
    data = tifffile.imread(str(tif_path))
    
    # Shape is (512, 512, 5) - multi-band float32
    # Take first visible band
    if data.ndim == 3:
        band = data[:, :, 0]
    else:
        band = data
    
    # Normalize float32 [0, max] to uint8 [0, 255]
    band = band.astype(np.float64)
    if band.max() > band.min():
        band = (band - band.min()) / (band.max() - band.min()) * 255.0
    band = np.clip(band, 0, 255).astype(np.uint8)
    
    return band


def characterise_image(image, stem, metadata_row=None):
    """
    Compute image characteristics for stratified sampling.
    
    Returns dict with: contrast, mean_intensity, std_intensity, 
                       incidence_angle (from metadata)
    """
    mean_val = float(np.mean(image))
    std_val = float(np.std(image))
    
    # Contrast metric: coefficient of variation
    contrast = std_val / max(mean_val, 1)
    
    # Dynamic range
    dynamic_range = float(np.max(image)) - float(np.min(image))
    
    info = {
        'stem': stem,
        'mean_intensity': mean_val,
        'std_intensity': std_val,
        'contrast': contrast,
        'dynamic_range': dynamic_range,
        'incidence_angle': None,
    }
    
    if metadata_row is not None:
        info['incidence_angle'] = float(metadata_row.get('INCIDENCE_ANGLE', 0))
    
    return info


def categorise_image(info, crater_stats):
    """
    Assign category labels for stratified sampling.
    
    Categories:
      contrast:     low / medium / high
      illumination: low_angle / high_angle / mixed
      crater_size:  small / large
      terrain:      clean / complex
    """
    # Contrast category (based on coefficient of variation)
    c = info['contrast']
    if c < 0.15:
        contrast_cat = 'low'
    elif c < 0.35:
        contrast_cat = 'medium'
    else:
        contrast_cat = 'high'
    
    # Illumination category (based on incidence angle)
    ia = info.get('incidence_angle')
    if ia is not None:
        if ia < 40:
            illum_cat = 'low_angle'
        elif ia > 70:
            illum_cat = 'high_angle'
        else:
            illum_cat = 'mixed'
    else:
        illum_cat = 'mixed'
    
    # Crater size (based on annotation bbox areas)
    if crater_stats['max_bbox_area'] < 3000:
        size_cat = 'small'
    else:
        size_cat = 'large'
    
    # Terrain complexity (based on number of craters)
    if crater_stats['n_craters'] <= 50:
        terrain_cat = 'clean'
    else:
        terrain_cat = 'complex'
    
    return {
        'contrast': contrast_cat,
        'illumination': illum_cat,
        'crater_size': size_cat,
        'terrain': terrain_cat,
    }


def get_crater_stats(annotations, image_id):
    """Get crater statistics for an image from COCO annotations."""
    image_anns = [a for a in annotations if a['image_id'] == image_id]
    
    if not image_anns:
        return {'n_craters': 0, 'max_bbox_area': 0, 'mean_bbox_area': 0}
    
    areas = [a['area'] for a in image_anns]
    return {
        'n_craters': len(image_anns),
        'max_bbox_area': max(areas),
        'mean_bbox_area': np.mean(areas),
    }


# ============================================================
# STEP 2: Stratified sampling -- select 30 images
# ============================================================

def stratified_sample(all_info, target_per_category=3):
    """
    Select 30 images using stratified sampling across 10 categories.
    
    Categories (3 images each):
      1. Low contrast
      2. Medium contrast  
      3. High contrast
      4. Low incidence angle (soft shadows)
      5. High incidence angle (harsh shadows)
      6. Mixed illumination
      7. Small crater rim
      8. Large crater rim
      9. Clean terrain (isolated craters)
      10. Complex terrain (overlapping craters)
    """
    # Sort candidates by category
    buckets = {
        'contrast_low': [],
        'contrast_medium': [],
        'contrast_high': [],
        'illum_low_angle': [],
        'illum_high_angle': [],
        'illum_mixed': [],
        'crater_small': [],
        'crater_large': [],
        'terrain_clean': [],
        'terrain_complex': [],
    }
    
    for info in all_info:
        cats = info['categories']
        buckets[f"contrast_{cats['contrast']}"].append(info)
        buckets[f"illum_{cats['illumination']}"].append(info)
        buckets[f"crater_{cats['crater_size']}"].append(info)
        buckets[f"terrain_{cats['terrain']}"].append(info)
    
    selected_stems = set()
    selected = []
    
    # Priority order: pick from each category in order
    category_order = [
        'contrast_low', 'contrast_medium', 'contrast_high',
        'illum_low_angle', 'illum_high_angle', 'illum_mixed',
        'crater_small', 'crater_large',
        'terrain_clean', 'terrain_complex',
    ]
    
    np.random.seed(42)  # Reproducibility
    
    for cat_name in category_order:
        candidates = [x for x in buckets[cat_name] if x['stem'] not in selected_stems]
        
        if not candidates:
            print(f"  WARNING: No candidates for category '{cat_name}', using any available")
            candidates = [x for x in all_info if x['stem'] not in selected_stems]
        
        # Shuffle and pick
        np.random.shuffle(candidates)
        n_pick = min(target_per_category, len(candidates))
        
        for i in range(n_pick):
            info = candidates[i]
            selected_stems.add(info['stem'])
            info['selected_category'] = cat_name
            selected.append(info)
    
    print(f"\n  Selected {len(selected)} images via stratified sampling")
    for cat_name in category_order:
        cat_items = [s for s in selected if s['selected_category'] == cat_name]
        print(f"    {cat_name}: {len(cat_items)} images")
    
    return selected


# ============================================================
# STEP 3: Extract patches and rasterise masks
# ============================================================

def find_best_crater_center(annotations, image_id, image_shape):
    """Find the largest crater center for patch extraction."""
    image_anns = [a for a in annotations if a['image_id'] == image_id]
    
    if not image_anns:
        # Default to image center
        return image_shape[0] // 2, image_shape[1] // 2
    
    # Pick the largest crater by area
    best_ann = max(image_anns, key=lambda a: a['area'])
    bbox = best_ann['bbox']  # [x, y, w, h]
    cx = int(bbox[0] + bbox[2] / 2)
    cy = int(bbox[1] + bbox[3] / 2)
    
    return cy, cx


def extract_patch(image, cy, cx, patch_size):
    """Extract a square patch centered at (cy, cx), handling boundary clipping."""
    h, w = image.shape[:2]
    half = patch_size // 2
    
    # Compute bounds with boundary clamping
    y_start = max(0, cy - half)
    x_start = max(0, cx - half)
    y_end = y_start + patch_size
    x_end = x_start + patch_size
    
    # Ensure we don't go off the edge
    if y_end > h:
        y_end = h
        y_start = h - patch_size
    if x_end > w:
        x_end = w
        x_start = w - patch_size
    
    y_start = max(0, y_start)
    x_start = max(0, x_start)
    
    return image[y_start:y_end, x_start:x_end], (y_start, x_start)


def rasterise_rim_mask(annotations, image_id, h=512, w=512, rim_width=2):
    """Rasterise crater rim from COCO polygons."""
    mask = np.zeros((h, w), dtype=np.uint8)
    image_anns = [a for a in annotations if a['image_id'] == image_id]
    
    for ann in image_anns:
        if 'segmentation' not in ann or not ann['segmentation']:
            continue
        for polygon in ann['segmentation']:
            pts = np.array(polygon, dtype=np.int32).reshape(-1, 2)
            cv2.polylines(mask, [pts], isClosed=True, color=255, thickness=rim_width)
    
    return mask


# ============================================================
# STEP 4: Run classical pipeline and evaluate
# ============================================================

def evaluate_patch(image_patch, mask_patch, patch_name):
    """Run all classical methods and compute metrics against GT mask."""
    results = []
    
    # Skip if mask is all zeros (no edges in this patch)
    if np.sum(mask_patch > 0) == 0:
        return None
    
    # Sobel
    sobel_mag = sobel_edge(image_patch)
    sobel_bin, _ = sobel_edge_binary(image_patch)
    m = compute_all_metrics(sobel_bin, sobel_mag, mask_patch, "Sobel")
    m['patch_name'] = patch_name
    results.append(m)
    
    # Canny
    canny_bin = canny_edge_auto(image_patch)
    m = compute_all_metrics(canny_bin, canny_bin, mask_patch, "Canny")
    m['patch_name'] = patch_name
    results.append(m)
    
    # Robinson
    rob_bin, rob_mag, rob_dir = robinson_edge_binary(image_patch)
    m = compute_all_metrics(rob_bin, rob_mag, mask_patch, "Robinson")
    m['patch_name'] = patch_name
    m['dominant_directions'] = str(np.unique(rob_dir).tolist())
    results.append(m)
    
    return results


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():
    print("=" * 70)
    print("PHASE 1 -- COMPLETE PIPELINE")
    print("Dataset Curation -> Patch Extraction -> Classical Evaluation")
    print("=" * 70)
    
    # ----------------------------------------------------------
    # 1. Load annotations and metadata
    # ----------------------------------------------------------
    print("\n[1/6] Loading annotations and metadata...")
    
    # Load test and val annotations
    all_images_info = []
    all_annotations = []
    image_id_to_split = {}
    stem_to_image_id = {}
    
    for split in ["test", "val"]:
        ann_path = ANNOTATIONS_DIR / f"{split}.json"
        if not ann_path.exists():
            print(f"  WARNING: {split}.json not found, skipping")
            continue
        
        with open(ann_path) as f:
            data = json.load(f)
        
        for img_info in data['images']:
            image_id = img_info['id']
            stem = Path(img_info['file_name']).stem
            image_id_to_split[image_id] = split
            stem_to_image_id[stem] = (image_id, split)
            all_images_info.append(img_info)
        
        # Offset IDs for val split to avoid collision
        all_annotations.extend(data['annotations'])
        
        print(f"  {split}: {len(data['images'])} images, "
              f"{len(data['annotations'])} annotations")
    
    # Load metadata for incidence angles
    metadata = {}
    try:
        import pandas as pd
        meta_path = ANNOTATIONS_DIR / "metadata.parquet"
        if meta_path.exists():
            df = pd.read_parquet(meta_path)
            for _, row in df.iterrows():
                stem = Path(row['WAC_VIS_TILE']).stem
                metadata[stem] = row
            print(f"  Metadata loaded: {len(metadata)} entries")
    except Exception as e:
        print(f"  Metadata not available: {e}")
    
    # ----------------------------------------------------------
    # 2. Characterise all images
    # ----------------------------------------------------------
    print("\n[2/6] Characterising all images for stratified sampling...")
    
    tiff_files = sorted(IMAGES_DIR.glob("*.tif"))
    print(f"  Found {len(tiff_files)} TIFF files")
    
    all_info = []
    for tif_path in tiff_files:
        stem = tif_path.stem
        
        # Check if this image has annotations
        if stem not in stem_to_image_id:
            continue
        
        try:
            image = load_sombench_image(tif_path)
        except Exception as e:
            print(f"  ERROR loading {stem}: {e}")
            continue
        
        # Get metadata row if available
        meta_row = metadata.get(stem)
        
        # Characterise image
        info = characterise_image(image, stem, meta_row)
        
        # Get crater statistics
        image_id, split = stem_to_image_id[stem]
        crater_stats = get_crater_stats(all_annotations, image_id)
        info['crater_stats'] = crater_stats
        info['image_id'] = image_id
        info['split'] = split
        
        # Categorise
        info['categories'] = categorise_image(info, crater_stats)
        
        all_info.append(info)
    
    print(f"  Characterised {len(all_info)} images")
    
    # Print distribution
    from collections import Counter
    for cat_key in ['contrast', 'illumination', 'crater_size', 'terrain']:
        dist = Counter(i['categories'][cat_key] for i in all_info)
        print(f"    {cat_key}: {dict(dist)}")
    
    # ----------------------------------------------------------
    # 3. Stratified sampling -- select 30
    # ----------------------------------------------------------
    print("\n[3/6] Performing stratified sampling...")
    selected = stratified_sample(all_info, target_per_category=3)
    
    # Save selection to CSV
    selection_csv = SOMBENCH_DIR / "selected_30_images.csv"
    with open(selection_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['stem', 'category', 'split', 'contrast', 'mean_intensity',
                         'incidence_angle', 'n_craters', 'max_crater_area'])
        for s in selected:
            writer.writerow([
                s['stem'], s['selected_category'], s['split'],
                f"{s['contrast']:.3f}", f"{s['mean_intensity']:.1f}",
                s.get('incidence_angle', ''), s['crater_stats']['n_craters'],
                f"{s['crater_stats']['max_bbox_area']:.0f}"
            ])
    print(f"  Selection saved to {selection_csv}")
    
    # ----------------------------------------------------------
    # 4. Extract patches and rasterise GT masks
    # ----------------------------------------------------------
    print("\n[4/6] Extracting patches and rasterising ground truth masks...")
    
    patches_8 = []
    patches_16 = []
    
    for info in selected:
        stem = info['stem']
        image_id = info['image_id']
        
        # Load full image
        tif_path = IMAGES_DIR / f"{stem}.tif"
        full_image = load_sombench_image(tif_path)
        
        # Rasterise rim mask for the full image
        full_mask = rasterise_rim_mask(all_annotations, image_id)
        
        # Find best crater center
        cy, cx = find_best_crater_center(all_annotations, image_id, full_image.shape)
        
        # Extract patches at both sizes
        for patch_size, patches_list in [(8, patches_8), (16, patches_16)]:
            img_patch, (y0, x0) = extract_patch(full_image, cy, cx, patch_size)
            mask_patch = full_mask[y0:y0+patch_size, x0:x0+patch_size]
            
            # Resize patches if extraction failed
            if img_patch.shape != (patch_size, patch_size):
                img_patch = cv2.resize(full_image, (patch_size, patch_size),
                                       interpolation=cv2.INTER_AREA)
                mask_patch = cv2.resize(full_mask, (patch_size, patch_size),
                                        interpolation=cv2.INTER_NEAREST)
            
            patch_name = f"{stem}_{patch_size}x{patch_size}"
            
            # Save patch and mask
            Image.fromarray(img_patch).save(PATCHES_DIR / f"{patch_name}.png")
            Image.fromarray(mask_patch).save(MASKS_DIR / f"{patch_name}_mask.png")
            
            patches_list.append({
                'name': patch_name,
                'stem': stem,
                'size': patch_size,
                'image': img_patch,
                'mask': mask_patch,
                'category': info['selected_category'],
                'has_edges': np.sum(mask_patch > 0) > 0,
            })
    
    print(f"  Extracted {len(patches_8)} 8x8 patches and {len(patches_16)} 16x16 patches")
    
    edge_patches_8 = [p for p in patches_8 if p['has_edges']]
    edge_patches_16 = [p for p in patches_16 if p['has_edges']]
    print(f"  With edges: {len(edge_patches_8)} (8x8), {len(edge_patches_16)} (16x16)")
    
    # ----------------------------------------------------------
    # 5. Run classical pipeline on all patches
    # ----------------------------------------------------------
    print("\n[5/6] Running classical edge detection on all patches...")
    
    all_results = []
    
    for patch_info in patches_8 + patches_16:
        if not patch_info['has_edges']:
            continue
        
        metrics = evaluate_patch(
            patch_info['image'], patch_info['mask'], patch_info['name']
        )
        
        if metrics:
            for m in metrics:
                m['size'] = patch_info['size']
                m['category'] = patch_info['category']
            all_results.extend(metrics)
    
    print(f"  Computed {len(all_results)} metric evaluations")
    
    # ----------------------------------------------------------
    # 6. Save results and print summary
    # ----------------------------------------------------------
    print("\n[6/6] Saving results...")
    
    # Save to CSV
    results_csv = RESULTS_DIR / "tables" / "classical_baseline_results.csv"
    results_csv.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = ['patch_name', 'size', 'category', 'method', 
                  'f1_exact', 'f1_1px', 'f1_2px',
                  'precision_exact', 'recall_exact', 'iou', 'chamfer', 'pr_auc']
    
    with open(results_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for r in all_results:
            # Round numeric values
            for k in ['f1_exact', 'f1_1px', 'f1_2px', 'precision_exact', 
                       'recall_exact', 'iou', 'chamfer', 'pr_auc']:
                if k in r:
                    r[k] = f"{r[k]:.4f}"
            writer.writerow(r)
    
    print(f"  Results saved to {results_csv}")
    
    # Print summary table
    print("\n" + "=" * 70)
    print("CLASSICAL BASELINE RESULTS -- SUMMARY")
    print("=" * 70)
    
    # Aggregate by method and size
    from collections import defaultdict
    agg = defaultdict(list)
    for r in all_results:
        key = (r['method'], r['size'])
        agg[key].append(float(r['f1_exact']))
    
    print(f"\n{'Method':<12} {'Size':<8} {'Mean F1':<10} {'Std F1':<10} {'N':<5}")
    print("-" * 50)
    for (method, size), f1_values in sorted(agg.items()):
        mean_f1 = np.mean(f1_values)
        std_f1 = np.std(f1_values)
        n = len(f1_values)
        print(f"{method:<12} {size}x{size:<5} {mean_f1:<10.4f} {std_f1:<10.4f} {n:<5}")
    
    # Per-category breakdown
    print(f"\n{'Category':<20} {'Method':<12} {'Mean F1':<10} {'N':<5}")
    print("-" * 55)
    cat_agg = defaultdict(list)
    for r in all_results:
        cat_agg[(r['category'], r['method'])].append(float(r['f1_exact']))
    
    for (cat, method), f1_values in sorted(cat_agg.items()):
        mean_f1 = np.mean(f1_values)
        print(f"{cat:<20} {method:<12} {mean_f1:<10.4f} {len(f1_values):<5}")
    
    print("\n" + "=" * 70)
    print("Phase 1 Complete!")
    print(f"  Selected images: {selection_csv}")
    print(f"  Patches: {PATCHES_DIR}")
    print(f"  GT masks: {MASKS_DIR}")
    print(f"  Results: {results_csv}")
    print("=" * 70)


if __name__ == "__main__":
    main()
