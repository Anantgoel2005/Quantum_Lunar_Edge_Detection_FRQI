"""
Evaluation Metrics for Edge Detection

Primary metrics:
  - Boundary F1 (exact, 1-pixel tolerance, 2-pixel tolerance)
  - Precision, Recall
  - IoU (Jaccard index)
  - Chamfer Distance
  - PR-AUC (full precision-recall curve)

All metrics compare a predicted edge map against an independent ground truth mask.
Classical baselines are NOT ground truth — they are evaluated the same way.
"""
import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt
from sklearn.metrics import precision_recall_curve, average_precision_score


def _binarize(edge_map, threshold=128):
    """Convert continuous edge map to binary (0/1)."""
    if edge_map.max() <= 1.0:
        return (edge_map > 0.5).astype(np.uint8)
    return (edge_map >= threshold).astype(np.uint8)


def boundary_f1(pred, gt, tolerance=0):
    """
    Compute boundary F1 score with optional pixel tolerance.
    
    Args:
        pred: predicted binary edge map (2D, uint8, 0 or 255)
        gt: ground truth binary edge map (2D, uint8, 0 or 255)
        tolerance: pixel tolerance (0=exact, 1=1px, 2=2px)
    
    Returns:
        f1: F1 score (0.0 to 1.0)
        precision: precision score
        recall: recall score
    """
    pred_bin = _binarize(pred)
    gt_bin = _binarize(gt)
    
    if tolerance > 0:
        # Dilate GT mask by tolerance pixels
        struct = np.ones((2 * tolerance + 1, 2 * tolerance + 1))
        gt_dilated = binary_dilation(gt_bin, structure=struct).astype(np.uint8)
        pred_dilated = binary_dilation(pred_bin, structure=struct).astype(np.uint8)
        
        # TP: predicted edges within tolerance of GT
        tp_precision = np.sum(pred_bin * gt_dilated)
        tp_recall = np.sum(gt_bin * pred_dilated)
        
        pred_total = np.sum(pred_bin)
        gt_total = np.sum(gt_bin)
        
        precision = tp_precision / max(pred_total, 1)
        recall = tp_recall / max(gt_total, 1)
    else:
        # Exact match
        tp = np.sum(pred_bin * gt_bin)
        pred_total = np.sum(pred_bin)
        gt_total = np.sum(gt_bin)
        
        precision = tp / max(pred_total, 1)
        recall = tp / max(gt_total, 1)
    
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    
    return f1, precision, recall


def iou_score(pred, gt):
    """
    Compute Intersection over Union (Jaccard index) on edge pixels.
    
    Args:
        pred: predicted binary edge map
        gt: ground truth binary edge map
    
    Returns:
        iou: IoU score (0.0 to 1.0)
    """
    pred_bin = _binarize(pred)
    gt_bin = _binarize(gt)
    
    intersection = np.sum(pred_bin * gt_bin)
    union = np.sum(np.clip(pred_bin + gt_bin, 0, 1))
    
    return intersection / max(union, 1)


def chamfer_distance(pred, gt):
    """
    Compute Chamfer distance between predicted and GT edge maps.
    Mean of (mean nearest distance from pred to GT, mean nearest distance from GT to pred).
    
    Lower is better. 0 = perfect match.
    
    Args:
        pred: predicted binary edge map
        gt: ground truth binary edge map
    
    Returns:
        chamfer: mean bidirectional Chamfer distance (in pixels)
    """
    pred_bin = _binarize(pred).astype(bool)
    gt_bin = _binarize(gt).astype(bool)
    
    if not np.any(pred_bin) or not np.any(gt_bin):
        return float('inf')
    
    # Distance transform: distance of each pixel to nearest True pixel
    dt_pred = distance_transform_edt(~pred_bin)
    dt_gt = distance_transform_edt(~gt_bin)
    
    # Mean distance from GT edge pixels to nearest predicted edge pixel
    gt_to_pred = np.mean(dt_pred[gt_bin])
    # Mean distance from predicted edge pixels to nearest GT edge pixel
    pred_to_gt = np.mean(dt_gt[pred_bin])
    
    return (gt_to_pred + pred_to_gt) / 2.0


def pr_auc(pred_continuous, gt, num_thresholds=100):
    """
    Compute average precision (step-integrated PR area, including tied scores).
    
    Args:
        pred_continuous: continuous edge strength map (0-255 uint8 or 0-1 float)
        gt: ground truth binary edge map
        num_thresholds: number of threshold levels to sweep
    
    Returns:
        auc_score: area under the PR curve
        precisions: array of precision values
        recalls: array of recall values
        thresholds: array of thresholds used
    """
    gt_bin = _binarize(gt).flatten()
    
    # Normalize to 0-1
    pred_flat = pred_continuous.flatten().astype(np.float64)
    if pred_flat.max() > 1.0:
        pred_flat = pred_flat / 255.0
    
    if np.sum(gt_bin) == 0:
        return 0.0, np.array([0]), np.array([0]), np.array([0])
    
    precisions, recalls, thresholds = precision_recall_curve(gt_bin, pred_flat)
    auc_score = average_precision_score(gt_bin, pred_flat)
    
    return auc_score, precisions, recalls, thresholds


def compute_all_metrics(pred_binary, pred_continuous, gt, method_name=""):
    """
    Compute all edge quality metrics.
    
    Args:
        pred_binary: binary edge map (uint8, 0/255)
        pred_continuous: continuous edge strength map (uint8, 0-255)
        gt: ground truth binary mask (uint8, 0/255)
        method_name: name of the method (for printing)
    
    Returns:
        dict of all metric values
    """
    f1_exact, p_exact, r_exact = boundary_f1(pred_binary, gt, tolerance=0)
    f1_1px, p_1px, r_1px = boundary_f1(pred_binary, gt, tolerance=1)
    f1_2px, p_2px, r_2px = boundary_f1(pred_binary, gt, tolerance=2)
    iou = iou_score(pred_binary, gt)
    chamfer = chamfer_distance(pred_binary, gt)
    auc_val, _, _, _ = pr_auc(pred_continuous, gt)
    
    metrics = {
        'method': method_name,
        'f1_exact': f1_exact,
        'precision_exact': p_exact,
        'recall_exact': r_exact,
        'f1_1px': f1_1px,
        'f1_2px': f1_2px,
        'iou': iou,
        'chamfer': chamfer,
        'pr_auc': auc_val,
    }
    
    return metrics


def print_metrics(metrics):
    """Pretty-print a metrics dictionary."""
    name = metrics.get('method', 'Unknown')
    print(f"  {name}:")
    print(f"    F1 (exact):  {metrics['f1_exact']:.4f}")
    print(f"    F1 (1px):    {metrics['f1_1px']:.4f}")
    print(f"    F1 (2px):    {metrics['f1_2px']:.4f}")
    print(f"    Precision:   {metrics['precision_exact']:.4f}")
    print(f"    Recall:      {metrics['recall_exact']:.4f}")
    print(f"    IoU:         {metrics['iou']:.4f}")
    print(f"    Chamfer:     {metrics['chamfer']:.4f}")
    print(f"    PR-AUC:      {metrics['pr_auc']:.4f}")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    from PIL import Image
    
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from classical.classical_pipeline import run_classical_pipeline
    
    # Test on circle_8x8 against its ground truth mask
    img_path = (Path(__file__).resolve().parents[1] / 'data/synthetic/images/circle_8x8.png')
    mask_path = (Path(__file__).resolve().parents[1] / 'data/synthetic/masks/circle_8x8_mask.png')
    
    img = np.array(Image.open(img_path))
    gt = np.array(Image.open(mask_path))
    
    results = run_classical_pipeline(img)
    
    print("=" * 60)
    print("Evaluation Metrics Test - circle_8x8 vs GT mask")
    print("=" * 60)
    
    for method, binary_key, cont_key in [
        ("Sobel", "sobel_binary", "sobel_magnitude"),
        ("Canny", "canny", "canny"),
        ("Robinson", "robinson_binary", "robinson_magnitude"),
    ]:
        m = compute_all_metrics(
            results[binary_key], results[cont_key], gt, method_name=method
        )
        print_metrics(m)
    
    print("\n" + "=" * 60)
    print("Evaluation metrics: OK")
    print("=" * 60)
