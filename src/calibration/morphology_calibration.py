"""
Empirical morphology calibration for ViDEC-Inspect v0.2.

Given a directory of binary defect masks (PNG, foreground > 0), fit
lognormal priors for:

- Crack: length (m), mean width (mm), max width (mm), tortuosity, branch
  count, orientation.
- Spall: area (m^2), perimeter (m), eccentricity, boundary irregularity
  proxy.

The calibration is purely geometric (uses skimage skeletonize / OpenCV
moments / fitEllipse) and requires a pixel_to_meter scale to produce
metric outputs. If unavailable, a representative scale is assumed and
documented in the provenance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import cv2
import numpy as np
from scipy import stats as sstats
from skimage.morphology import skeletonize


def _load_mask(path: Path) -> Optional[np.ndarray]:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    return (img > 0).astype(np.uint8)


def _crack_metrics(mask: np.ndarray, pixel_to_meter: float) -> Optional[Dict]:
    area_px = int(mask.sum())
    if area_px < 30:
        return None
    sk = skeletonize(mask.astype(bool)).astype(np.uint8)
    sk_len_px = int(sk.sum())
    if sk_len_px < 5:
        return None

    length_m = sk_len_px * float(pixel_to_meter)
    mean_width_px = area_px / max(sk_len_px, 1)
    mean_width_mm = mean_width_px * float(pixel_to_meter) * 1000.0

    ys, xs = np.where(sk > 0)
    chord_len_px = float(np.hypot(xs.max() - xs.min(), ys.max() - ys.min()))
    tortuosity = float(sk_len_px / max(chord_len_px, 1.0))

    # Max width proxy: distance transform inside mask, max value * 2 (radius * 2 -> width).
    dt = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    max_width_mm = float(dt.max() * 2.0 * pixel_to_meter * 1000.0)

    # Orientation via PCA of skeleton points.
    coords = np.stack([xs.astype(np.float32), ys.astype(np.float32)], axis=1)
    coords -= coords.mean(axis=0, keepdims=True)
    if coords.shape[0] >= 5:
        cov = np.cov(coords.T)
        eigvals, eigvecs = np.linalg.eigh(cov)
        v = eigvecs[:, -1]
        orientation_deg = float(np.rad2deg(np.arctan2(v[1], v[0])) % 180.0)
    else:
        orientation_deg = float("nan")

    return {
        "length_m": length_m,
        "mean_width_mm": mean_width_mm,
        "max_width_mm": max_width_mm,
        "tortuosity": tortuosity,
        "orientation_deg": orientation_deg,
        "area_px": area_px,
        "skeleton_len_px": sk_len_px,
    }


def _spall_metrics(mask: np.ndarray, pixel_to_meter: float) -> Optional[Dict]:
    area_px = int(mask.sum())
    if area_px < 100:
        return None
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    perimeter_px = float(cv2.arcLength(contour, True))
    area_m2 = area_px * (float(pixel_to_meter) ** 2)
    perimeter_m = perimeter_px * float(pixel_to_meter)

    eccentricity = float("nan")
    if contour.shape[0] >= 5:
        try:
            (_, axes, _) = cv2.fitEllipse(contour)
            a = max(axes) / 2.0
            b = min(axes) / 2.0
            if a > 0:
                eccentricity = float(np.sqrt(max(0.0, 1.0 - (b / a) ** 2)))
        except cv2.error:
            pass

    # Boundary irregularity: variance of polar radius from centroid, normalized.
    M = cv2.moments(mask)
    if M["m00"] > 0:
        cx, cy = M["m10"] / M["m00"], M["m01"] / M["m00"]
        pts = contour.reshape(-1, 2).astype(np.float32)
        r = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
        boundary_irregularity = float(r.std() / max(r.mean(), 1e-6))
    else:
        boundary_irregularity = float("nan")

    return {
        "area_m2": area_m2,
        "perimeter_m": perimeter_m,
        "eccentricity": eccentricity,
        "boundary_irregularity": boundary_irregularity,
        "area_px": area_px,
    }


def _fit_lognormal(values: List[float]) -> Optional[Dict]:
    arr = np.asarray([v for v in values if np.isfinite(v) and v > 0], dtype=np.float64)
    if arr.size < 5:
        return None
    # Fit lognormal with floc=0 so we recover mu = mean of log(x) and sigma = std of log(x).
    shape, loc, scale = sstats.lognorm.fit(arr, floc=0.0)
    mean_log = float(np.log(scale))
    std_log = float(shape)
    return {
        "type": "lognormal",
        "mean_log": mean_log,
        "std_log": std_log,
        "clip": [float(np.percentile(arr, 1)), float(np.percentile(arr, 99))],
        "n": int(arr.size),
        "median": float(np.median(arr)),
        "p10": float(np.percentile(arr, 10)),
        "p90": float(np.percentile(arr, 90)),
    }


def _percentile_range(values: List[float], lo: float = 10, hi: float = 90) -> Optional[List[float]]:
    arr = np.asarray([v for v in values if np.isfinite(v)], dtype=np.float64)
    if arr.size < 3:
        return None
    return [float(np.percentile(arr, lo)), float(np.percentile(arr, hi))]


def fit_crack_morphology(
    mask_paths: Iterable[Path],
    pixel_to_meter: float,
) -> Dict:
    """Fit empirical morphology priors for cracks from a list of mask paths."""
    metrics: List[Dict] = []
    for p in mask_paths:
        m = _load_mask(p)
        if m is None:
            continue
        r = _crack_metrics(m, pixel_to_meter)
        if r is not None:
            metrics.append(r)

    if not metrics:
        return {"num_samples": 0}

    lengths = [m["length_m"] for m in metrics]
    widths = [m["mean_width_mm"] for m in metrics]
    max_widths = [m["max_width_mm"] for m in metrics]
    tort = [m["tortuosity"] for m in metrics]
    orient = [m["orientation_deg"] for m in metrics]

    return {
        "num_samples": len(metrics),
        "pixel_to_meter": float(pixel_to_meter),
        "length_distribution": _fit_lognormal(lengths),
        "width_distribution": _fit_lognormal(widths),
        "max_width_distribution": _fit_lognormal(max_widths),
        "tortuosity_range": _percentile_range(tort),
        "orientation_range_deg": _percentile_range(orient),
    }


def fit_spall_morphology(
    mask_paths: Iterable[Path],
    pixel_to_meter: float,
) -> Dict:
    """Fit empirical morphology priors for spalls from a list of mask paths."""
    metrics: List[Dict] = []
    for p in mask_paths:
        m = _load_mask(p)
        if m is None:
            continue
        r = _spall_metrics(m, pixel_to_meter)
        if r is not None:
            metrics.append(r)

    if not metrics:
        return {"num_samples": 0}

    areas = [m["area_m2"] for m in metrics]
    perim = [m["perimeter_m"] for m in metrics]
    ecc = [m["eccentricity"] for m in metrics]
    irreg = [m["boundary_irregularity"] for m in metrics]

    return {
        "num_samples": len(metrics),
        "pixel_to_meter": float(pixel_to_meter),
        "area_distribution": _fit_lognormal(areas),
        "perimeter_distribution": _fit_lognormal(perim),
        "eccentricity_range": _percentile_range(ecc),
        "boundary_irregularity_range": _percentile_range(irreg),
    }
