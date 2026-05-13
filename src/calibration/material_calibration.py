"""
Empirical material (concrete substrate) calibration for ViDEC-Inspect v0.2.

Given a corpus of dry- or wet-concrete patches (RGB), estimate distributional
priors for base luminance, color bias, micro-texture amplitude (Laplacian
variance proxy), and stain prevalence (high-saturation patch fraction).

The output augments src/synthesis/material_model.py with empirically
informed ranges instead of hard-coded constants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import cv2
import numpy as np


def _per_patch_stats(image_path: Path) -> Optional[Dict]:
    img_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img_bgr is None:
        return None
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    gray = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)

    mu_rgb = rgb.reshape(-1, 3).mean(axis=0)
    base_luminance = float(gray.mean() / 255.0)
    micro_roughness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    color_bias = (mu_rgb - mu_rgb.mean()).tolist()

    hsv = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    sat = hsv[..., 1].astype(np.float32) / 255.0
    stain_fraction = float((sat > 0.30).mean())

    return {
        "image_path": str(image_path),
        "base_luminance": base_luminance,
        "micro_roughness": micro_roughness,
        "color_bias": [float(c) for c in color_bias],
        "stain_fraction": stain_fraction,
    }


def _percentile_range(values: List[float], lo: float = 10, hi: float = 90) -> Optional[List[float]]:
    arr = np.asarray([v for v in values if np.isfinite(v)], dtype=np.float64)
    if arr.size < 3:
        return None
    return [float(np.percentile(arr, lo)), float(np.percentile(arr, hi))]


def fit_material_priors(image_paths: Iterable[Path]) -> Dict:
    stats: List[Dict] = []
    for p in image_paths:
        s = _per_patch_stats(p)
        if s is not None:
            stats.append(s)
    if not stats:
        return {"num_samples": 0}

    lum = [s["base_luminance"] for s in stats]
    rough = [s["micro_roughness"] for s in stats]
    stain = [s["stain_fraction"] for s in stats]

    rough_arr = np.asarray(rough, dtype=np.float32)
    rough_norm = (rough_arr / max(float(rough_arr.max() + 1e-6), 1e-6)).tolist()

    return {
        "num_samples": len(stats),
        "base_luminance_range": _percentile_range(lum),
        "micro_roughness_range": _percentile_range(rough),
        "micro_roughness_normalized_range": _percentile_range(rough_norm),
        "stain_fraction_range": _percentile_range(stain),
    }
