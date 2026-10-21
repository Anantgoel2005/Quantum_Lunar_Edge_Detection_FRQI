"""BSDS-style multi-annotator boundary evaluation for development crops.

Uses exact sparse maximum-cardinality/minimum-distance matching, with SciPy,
and Guo-Hall thinning. Not certified equivalent to the Berkeley MATLAB binary.
"""
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import min_weight_full_bipartite_matching
from scipy.spatial import cKDTree
from skimage.morphology import thin

THRESHOLDS = np.arange(1, 32, dtype=float) / 32


def match_pixels(prediction, reference, distance):
    """Return unique flat pixel indices, maximizing matches then minimizing distance."""
    pred, gt = np.asarray(prediction, dtype=bool), np.asarray(reference, dtype=bool)
    if pred.ndim != 2 or pred.shape != gt.shape or not np.isfinite(distance) or distance < 0:
        raise ValueError('Expected same-shape 2D masks and finite nonnegative distance')
    pi, gi = np.flatnonzero(pred), np.flatnonzero(gt)
    if not len(pi) or not len(gi):
        return np.empty(0, dtype=int), np.empty(0, dtype=int)
    pp = np.column_stack(np.unravel_index(pi, pred.shape))
    gp = np.column_stack(np.unravel_index(gi, gt.shape))
    neighbours = cKDTree(gp).query_ball_point(pp, distance)
    counts = np.array([len(n) for n in neighbours])
    rows = np.repeat(np.arange(len(pi)), counts)
    cols = np.concatenate(neighbours).astype(int) if counts.sum() else np.empty(0, dtype=int)
    costs = np.linalg.norm(pp[rows] - gp[cols], axis=1) + 1
    # Every row has its own unmatched dummy. Its cost exceeds the sum of all
    # possible real-edge costs, making cardinality the first objective.
    penalty = (len(pi) + 1) * (distance + 1) + 1
    graph = csr_matrix((np.r_[costs, np.full(len(pi), penalty)],
                        (np.r_[rows, np.arange(len(pi))],
                         np.r_[cols, len(gi) + np.arange(len(pi))])),
                       shape=(len(pi), len(gi) + len(pi)))
    matched_rows, matched_cols = min_weight_full_bipartite_matching(graph)
    real = matched_cols < len(gi)
    return pi[matched_rows[real]], gi[matched_cols[real]]


def boundary_counts(prediction, references, max_distance=.0075, apply_thinning=True):
    prediction = np.asarray(prediction, dtype=bool)
    references = np.asarray(references, dtype=bool)
    if prediction.ndim != 2 or references.ndim != 3 or references.shape[1:] != prediction.shape or not len(references):
        raise ValueError('Expected 2D prediction and nonempty annotator x height x width references')
    if apply_thinning:
        prediction = thin(prediction)
    matched_pred = np.zeros(prediction.size, dtype=bool)
    count_r, sum_r = 0, 0
    distance = max_distance * np.hypot(*prediction.shape)
    for gt in references:
        p, g = match_pixels(prediction, gt, distance)
        matched_pred[p] = True
        count_r += len(g)
        sum_r += int(gt.sum())
    # Recall sums over annotators; precision counts prediction matches to ANY.
    return np.array([count_r, sum_r, int(matched_pred.sum()), int(prediction.sum())], dtype=float)


def evaluate_curve(strength, references, thresholds=THRESHOLDS):
    strength = np.asarray(strength, dtype=float)
    if not np.isfinite(strength).all() or np.any(strength < 0) or np.any(strength > 1 + 1e-12):
        raise ValueError('Expected finite strengths in [0,1]')
    counts = []
    previous, previous_count = None, None
    for threshold in thresholds:
        binary = strength >= threshold
        if previous is not None and np.array_equal(binary, previous):
            count = previous_count.copy()
        else:
            count = boundary_counts(binary, references)
        counts.append(count)
        previous, previous_count = binary, count
    return np.asarray(counts)


def scores(counts):
    counts = np.asarray(counts, dtype=float)
    recall = counts[..., 0] / np.maximum(counts[..., 1], 1)
    precision = counts[..., 2] / np.maximum(counts[..., 3], 1)
    f1 = 2 * precision * recall / np.maximum(precision + recall, 1e-30)
    return recall, precision, f1


def curve_summary(counts):
    recall, precision, f1 = scores(counts)
    best = int(np.argmax(f1))
    # Report an explicitly named 101-point interpolated boundary AP. Do not
    # confuse it with pixel AP in the earlier SomBench benchmark or MATLAB AP.
    grid = np.linspace(0, 1, 101)
    envelope = np.array([np.max(precision[recall >= r], initial=0) for r in grid])
    return {'best_f1': float(f1[best]), 'best_threshold': float(THRESHOLDS[best]),
            'precision': float(precision[best]), 'recall': float(recall[best]),
            'boundary_ap101': float(envelope.mean())}
