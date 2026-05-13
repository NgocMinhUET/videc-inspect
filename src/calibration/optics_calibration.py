"""
Empirical optics calibration for ViDEC-Inspect v0.2.

Given a corpus of underwater RGB images (no depth required), estimate
distributional priors for:

- channel-wise attenuation coefficient `beta_rgb`,
- backscatter color and strength,
- contrast scaling range,
- turbidity blur sigma range (proxy via inverse Laplacian variance),
- particle noise strength range.

Method (per image):

1. Estimate the veiling/backscatter color B_c per channel as the mean of the
   top-1% brightest pixels in a low-variance neighborhood (a coarse proxy
   for the "infinity" radiance B_c in the underwater image formation model).

2. Assume a neutral surface reference J_c (default 0.5 for grey concrete) and
   a representative range d_bar (default 2.0 m, calibratable).

3. Invert the simplified image formation equation
       mu_c = J_c * exp(-beta_c * d_bar) + B_c * (1 - exp(-beta_c * d_bar))
   for the *per-channel* transmittance t_c, then solve
       beta_c = -ln(t_c) / d_bar.
   When the inversion is ill-conditioned (e.g., mu_c close to B_c) we fall
   back to NaN and exclude the image from that channel's statistics.

4. Aggregate over the corpus: per-channel percentile ranges become the
   per-water-type bracketed priors. If water_type labels are supplied
   per image, they are grouped; otherwise, the corpus is auto-binned by
   contrast/color-cast quantile into clear / moderate / turbid.

Limitations (academic honesty):

- Without per-image depth, beta_c is identifiable only up to the assumed
  range d_bar. The output is therefore a *prior range*, not a measurement.
- The assumed J_c is a placeholder for a per-corpus reference; replace it
  with measured dry-concrete reflectance when available.
- Auto water-type binning is a convenience; if reviewer-grade calibration
  is required, supply human-labelled water_type per image.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np


_DEFAULT_REFERENCE_J = (0.50, 0.50, 0.50)
_DEFAULT_D_BAR_M = 2.0
_EPS = 1e-4


def compute_image_optics_stats(
    image_path: str,
    reference_J: Sequence[float] = _DEFAULT_REFERENCE_J,
    d_bar_m: float = _DEFAULT_D_BAR_M,
) -> Optional[Dict]:
    """Compute per-image optics statistics.

    Returns dict with means, stds, sharpness, color cast, estimated B_c,
    backscatter strength, and beta_rgb (under the J_c, d_bar assumptions).
    Returns None if the image is unreadable.
    """
    img_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img_bgr is None:
        return None
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    gray = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)

    mu_rgb = rgb.reshape(-1, 3).mean(axis=0)
    std_rgb = rgb.reshape(-1, 3).std(axis=0)
    gray_std = float(gray.std() / 255.0)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    color_cast = float(np.linalg.norm(mu_rgb - mu_rgb.mean()) / np.sqrt(3))

    # Backscatter color B_c via the dark-channel prior (He et al. 2010):
    # 1) per-pixel dark channel = min over channels (with a 7x7 erosion).
    # 2) take the top 0.1% brightest pixels in the dark channel.
    # 3) among those, the pixel with the highest intensity (mean RGB) is B_c.
    # This is the standard estimator for haze/veiling light and works much
    # better than a per-channel top-percentile heuristic on real images.
    dark = rgb.min(axis=2)
    kernel = np.ones((7, 7), np.uint8)
    dark_eroded = cv2.erode(dark, kernel)
    threshold = float(np.quantile(dark_eroded, 0.999))
    mask_bright = dark_eroded >= threshold
    if mask_bright.sum() == 0:
        B_rgb = np.array([float(rgb[..., c].max()) for c in range(3)], dtype=np.float32)
    else:
        candidates = rgb[mask_bright]  # Nx3
        intensities = candidates.mean(axis=1)
        idx = int(np.argmax(intensities))
        B_rgb = candidates[idx].astype(np.float32)

    backscatter_strength = float(B_rgb.mean())

    # Invert image formation to estimate beta_rgb under (reference_J, d_bar).
    J = np.asarray(reference_J, dtype=np.float32)
    beta_rgb = np.full(3, np.nan, dtype=np.float32)
    for c in range(3):
        gap_obs = float(B_rgb[c] - mu_rgb[c])  # how far observed mean from B
        gap_ref = float(B_rgb[c] - J[c])       # how far surface from B
        if gap_ref <= _EPS or gap_obs <= _EPS:
            continue
        t_c = gap_obs / gap_ref
        if not (0.0 < t_c < 1.0):
            continue
        beta_rgb[c] = float(-np.log(t_c) / max(d_bar_m, _EPS))

    return {
        "image_path": str(image_path),
        "mu_rgb": mu_rgb.tolist(),
        "std_rgb": std_rgb.tolist(),
        "gray_std": gray_std,
        "laplacian_var": laplacian_var,
        "color_cast": color_cast,
        "B_rgb": B_rgb.tolist(),
        "backscatter_strength": backscatter_strength,
        "beta_rgb": beta_rgb.tolist(),
        "reference_J": list(reference_J),
        "d_bar_m": float(d_bar_m),
    }


def estimate_beta_rgb_from_image(image_path: str, **kwargs) -> Optional[List[float]]:
    """Convenience wrapper returning just the estimated beta_rgb."""
    stats = compute_image_optics_stats(image_path, **kwargs)
    if stats is None:
        return None
    return stats["beta_rgb"]


def _auto_bin_water_type(stats: List[Dict]) -> List[str]:
    """Auto-bin images into clear/moderate/turbid using contrast + color cast.

    A lower-contrast and higher-color-cast image is binned to a more turbid
    class. The thresholds are corpus-relative quantiles.
    """
    if not stats:
        return []
    contrast = np.asarray([s["gray_std"] for s in stats], dtype=np.float32)
    color_cast = np.asarray([s["color_cast"] for s in stats], dtype=np.float32)

    contrast_loss = 1.0 - (contrast - contrast.min()) / max(
        float(contrast.max() - contrast.min()), _EPS
    )
    cc_norm = (color_cast - color_cast.min()) / max(
        float(color_cast.max() - color_cast.min()), _EPS
    )
    turbidity_score = 0.5 * contrast_loss + 0.5 * cc_norm

    labels = []
    q33 = float(np.quantile(turbidity_score, 0.33))
    q66 = float(np.quantile(turbidity_score, 0.66))
    for s in turbidity_score:
        if s < q33:
            labels.append("clear")
        elif s < q66:
            labels.append("moderate")
        else:
            labels.append("turbid")
    return labels


def _percentile_range(values: Sequence[float], lo: float = 10, hi: float = 90) -> Optional[List[float]]:
    arr = np.asarray([v for v in values if np.isfinite(v)], dtype=np.float32)
    if arr.size < 3:
        return None
    return [float(np.percentile(arr, lo)), float(np.percentile(arr, hi))]


def aggregate_optics_priors(
    per_image_stats: List[Dict],
    water_type_labels: Optional[Sequence[str]] = None,
    auto_bin_if_missing: bool = True,
    percentile_low: float = 10.0,
    percentile_high: float = 90.0,
) -> Dict:
    """Aggregate per-image stats into bracketed YAML-ready priors.

    Args:
        per_image_stats: list of dicts from compute_image_optics_stats.
        water_type_labels: optional list aligning to per_image_stats; if None
            and auto_bin_if_missing is True, the corpus is auto-binned.
        percentile_low / percentile_high: bracketing percentiles.

    Returns:
        dict with structure:
        {
            "water_types": {
                "clear": {beta_rgb, backscatter_strength, contrast_scale,
                          blur_sigma, particle_noise_strength, num_samples},
                "moderate": {...},
                "turbid": {...},
            },
            "global": { ... per-corpus aggregates ... },
            "method": { d_bar_m, reference_J, percentiles, auto_binned },
        }
    """
    if not per_image_stats:
        return {"water_types": {}, "global": {}, "method": {}}

    if water_type_labels is None:
        if auto_bin_if_missing:
            water_type_labels = _auto_bin_water_type(per_image_stats)
        else:
            water_type_labels = ["unlabeled"] * len(per_image_stats)

    by_class: Dict[str, List[Dict]] = {}
    for s, lbl in zip(per_image_stats, water_type_labels):
        by_class.setdefault(lbl, []).append(s)

    def _summarize(group: List[Dict]) -> Dict:
        if not group:
            return {}
        beta_r = [g["beta_rgb"][0] for g in group]
        beta_g = [g["beta_rgb"][1] for g in group]
        beta_b = [g["beta_rgb"][2] for g in group]
        bs = [g["backscatter_strength"] for g in group]
        contrast = [g["gray_std"] for g in group]
        lap = [g["laplacian_var"] for g in group]

        beta_r_med = float(np.nanmedian(beta_r)) if any(np.isfinite(beta_r)) else float("nan")
        beta_g_med = float(np.nanmedian(beta_g)) if any(np.isfinite(beta_g)) else float("nan")
        beta_b_med = float(np.nanmedian(beta_b)) if any(np.isfinite(beta_b)) else float("nan")

        # Map sharpness to inverse blur sigma proxy (heuristic, calibratable):
        # higher laplacian_var -> lower blur_sigma; we report a sigma proxy
        # bracket via sqrt(reciprocal-rescaled-laplacian).
        lap_arr = np.asarray(lap, dtype=np.float32)
        lap_norm = lap_arr / max(float(lap_arr.max() + 1e-6), 1e-6)
        blur_sigma_proxy = np.clip(np.sqrt(1.0 - lap_norm) * 3.0, 0.0, 3.0)

        return {
            "num_samples": len(group),
            "beta_rgb_median": [beta_r_med, beta_g_med, beta_b_med],
            "beta_r_range": _percentile_range(beta_r, percentile_low, percentile_high),
            "beta_g_range": _percentile_range(beta_g, percentile_low, percentile_high),
            "beta_b_range": _percentile_range(beta_b, percentile_low, percentile_high),
            "backscatter_strength_range": _percentile_range(bs, percentile_low, percentile_high),
            "contrast_scale_range": _percentile_range(contrast, percentile_low, percentile_high),
            "blur_sigma_proxy_range": _percentile_range(
                blur_sigma_proxy.tolist(), percentile_low, percentile_high
            ),
        }

    out: Dict[str, Dict] = {"water_types": {}, "global": {}, "method": {}}
    for cls in ("clear", "moderate", "turbid", "unlabeled"):
        if cls in by_class:
            out["water_types"][cls] = _summarize(by_class[cls])

    out["global"] = _summarize(per_image_stats)
    out["method"] = {
        "d_bar_m": float(per_image_stats[0]["d_bar_m"]),
        "reference_J": list(per_image_stats[0]["reference_J"]),
        "percentile_low": float(percentile_low),
        "percentile_high": float(percentile_high),
        "auto_binned": water_type_labels is not None and any(
            l in {"clear", "moderate", "turbid"} for l in water_type_labels
        ) and "water_type_labels_provided" not in out["method"],
        "num_images": len(per_image_stats),
    }
    return out


def iter_images_in_dir(image_dir: str, glob_patterns: Iterable[str] = ("*.png", "*.jpg", "*.jpeg")) -> List[Path]:
    """List image files under a directory (non-recursive by default)."""
    root = Path(image_dir)
    out: List[Path] = []
    if root.is_file():
        return [root]
    if not root.exists():
        return out
    for pat in glob_patterns:
        out.extend(sorted(root.rglob(pat)))
    return sorted(set(out))
