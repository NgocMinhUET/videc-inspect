"""
Underwater optical image formation for ViDEC-Inspect v0.2.

Implements a simplified Jaffe-McGlamery style channel-wise attenuation +
backscatter model with turbidity-dependent blur, contrast scaling, lighting
exposure, and noise.

The image formation equation is:

    I_c(x) = J_c(x) * exp(-beta_c * d(x))
             + B_c * (1 - exp(-beta_c * d(x)))
             + eta_c(x)

where c indexes RGB channels, d(x) is the metric range at pixel x, beta_c is
the channel-wise volumetric attenuation coefficient, B_c is the veiling
(backscatter) radiance, and eta_c is sensor/environment noise.

All outputs are deterministic for a given (seed, water_type, lighting_level).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
import yaml


_DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "configs" / "synthesis" / "underwater_optics.yaml"
)


def load_underwater_optics_config(config_path: Optional[str] = None) -> Dict:
    """Load the underwater optics YAML config."""
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _rng(seed: Optional[int]) -> np.random.Generator:
    return np.random.default_rng(seed)


def _sample_uniform(rng: np.random.Generator, lo_hi) -> float:
    lo, hi = float(lo_hi[0]), float(lo_hi[1])
    if hi <= lo:
        return lo
    return float(rng.uniform(lo, hi))


def _resolve_water_type(water_type: str, cfg: Dict) -> str:
    alias = cfg.get("clarity_alias", {}) or {}
    return alias.get(water_type, water_type)


def apply_underwater_optics(
    rgb_clean: np.ndarray,
    depth_map: np.ndarray,
    water_type: str = "moderate",
    lighting_level: str = "normal",
    seed: Optional[int] = None,
    config: Optional[Dict] = None,
) -> Tuple[np.ndarray, Dict]:
    """Apply the underwater image formation model to a clean RGB image.

    Args:
        rgb_clean: HxWx3 uint8 image, RGB channel order.
        depth_map: HxW float metric depth map (meters).
        water_type: 'clear' | 'moderate' | 'turbid' (or v0.1 alias 'murky').
        lighting_level: 'low' | 'normal' | 'high'.
        seed: integer seed for reproducibility. If None, fresh entropy.
        config: optional preloaded config dict; loaded from YAML if omitted.

    Returns:
        rgb_underwater: HxWx3 uint8 image (RGB).
        quality_metrics: dict with verification-relevant quality fields and
            the sampled physical parameters.
    """
    if rgb_clean.ndim != 3 or rgb_clean.shape[2] < 3:
        raise ValueError("rgb_clean must be HxWx3")
    if depth_map.shape != rgb_clean.shape[:2]:
        raise ValueError("depth_map shape must match rgb_clean spatial dims")

    if config is None:
        config = load_underwater_optics_config()

    water_type_resolved = _resolve_water_type(water_type, config)
    if water_type_resolved not in config["water_types"]:
        raise ValueError(
            f"Unknown water_type '{water_type}' (resolved '{water_type_resolved}'). "
            f"Known: {list(config['water_types'].keys())}"
        )
    if lighting_level not in config["lighting"]:
        raise ValueError(
            f"Unknown lighting_level '{lighting_level}'. "
            f"Known: {list(config['lighting'].keys())}"
        )

    rng = _rng(seed)
    w_cfg = config["water_types"][water_type_resolved]
    l_cfg = config["lighting"][lighting_level]

    beta_rgb = np.asarray(w_cfg["beta_rgb"], dtype=np.float32)
    bs_color = np.asarray(w_cfg["backscatter_color_rgb"], dtype=np.float32)
    bs_strength = _sample_uniform(rng, w_cfg["backscatter_strength"])
    blur_sigma = _sample_uniform(rng, w_cfg["blur_sigma"])
    contrast_scale = _sample_uniform(rng, w_cfg["contrast_scale"])
    particle_noise = _sample_uniform(rng, w_cfg["particle_noise_strength"])

    exposure = _sample_uniform(rng, l_cfg["exposure"])
    noise_level = _sample_uniform(rng, l_cfg["noise_level"])
    falloff = _sample_uniform(rng, l_cfg["falloff_strength"])

    H, W = rgb_clean.shape[:2]
    J = rgb_clean[..., :3].astype(np.float32) / 255.0
    d = np.clip(depth_map.astype(np.float32), 1e-3, None)

    # Lighting falloff: radial darkening centered on image (artificial light proxy).
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
    rr = np.sqrt(((xx - cx) / max(cx, 1.0)) ** 2 + ((yy - cy) / max(cy, 1.0)) ** 2)
    falloff_map = np.clip(1.0 - falloff * rr, 0.0, 1.0)
    J = J * falloff_map[..., None]

    # Pre-attenuation exposure (linear gain on signal).
    J = np.clip(J * exposure, 0.0, 1.5)

    # Channel-wise attenuation + additive backscatter, both functions of d(x).
    trans = np.exp(-beta_rgb[None, None, :] * d[..., None])
    backscatter = bs_color[None, None, :] * bs_strength
    I = J * trans + backscatter * (1.0 - trans)

    # Global contrast scaling (water-type dependent).
    I_mean = I.mean(axis=(0, 1), keepdims=True)
    I = (I - I_mean) * contrast_scale + I_mean

    # Turbidity-dependent isotropic Gaussian blur (multi-scattering proxy).
    if blur_sigma > 0.05:
        I = cv2.GaussianBlur(I, ksize=(0, 0), sigmaX=float(blur_sigma), sigmaY=float(blur_sigma))

    # Environmental + sensor noise.
    sigma_total = float(np.sqrt(noise_level ** 2 + particle_noise ** 2))
    if sigma_total > 0:
        I = I + rng.normal(0.0, sigma_total, size=I.shape).astype(np.float32)

    I = np.clip(I, 0.0, 1.0)
    rgb_underwater = (I * 255.0).astype(np.uint8)

    quality_metrics = compute_visibility_metrics(
        rgb_before=rgb_clean[..., :3],
        rgb_after=rgb_underwater,
        depth_map=depth_map,
    )
    quality_metrics.update({
        "water_type": water_type_resolved,
        "lighting_level": lighting_level,
        "beta_rgb": [float(b) for b in beta_rgb.tolist()],
        "backscatter_strength": float(bs_strength),
        "blur_sigma": float(blur_sigma),
        "contrast_scale": float(contrast_scale),
        "exposure": float(exposure),
        "noise_level": float(noise_level),
        "particle_noise_strength": float(particle_noise),
        "lighting_falloff": float(falloff),
    })
    return rgb_underwater, quality_metrics


def compute_visibility_metrics(
    rgb_before: np.ndarray,
    rgb_after: np.ndarray,
    depth_map: np.ndarray,
) -> Dict[str, float]:
    """Compute verification-aware quality metrics from a before/after pair.

    Args:
        rgb_before: HxWx3 uint8 image (RGB), pre-optics reference.
        rgb_after: HxWx3 uint8 image (RGB), post-optics observation.
        depth_map: HxW float metric depth map (m).

    Returns:
        metrics: dict with contrast_score, sharpness_score, visibility_score,
            color_cast_strength, mean_depth_m, valid_ratio.
    """
    after_f = rgb_after.astype(np.float32) / 255.0

    gray_after = cv2.cvtColor(rgb_after, cv2.COLOR_RGB2GRAY)
    sharpness_raw = float(cv2.Laplacian(gray_after, cv2.CV_64F).var())
    sharpness_score = float(1.0 - np.exp(-sharpness_raw / 500.0))

    contrast_score = float(np.clip(gray_after.std() / (128.0 * 0.35), 0.0, 1.0))

    mean_rgb = after_f.reshape(-1, 3).mean(axis=0)
    neutral = float(mean_rgb.mean())
    color_cast_strength = float(np.linalg.norm(mean_rgb - neutral) / np.sqrt(3))

    visibility_score = float(np.clip(
        contrast_score * (1.0 - 1.5 * color_cast_strength), 0.0, 1.0
    ))

    valid = np.isfinite(depth_map) & (depth_map > 0)
    mean_depth = float(depth_map[valid].mean()) if valid.any() else 0.0
    valid_ratio = float(valid.mean())

    return {
        "contrast_score": contrast_score,
        "sharpness_score": sharpness_score,
        "visibility_score": visibility_score,
        "color_cast_strength": color_cast_strength,
        "mean_depth_m": mean_depth,
        "valid_ratio": valid_ratio,
    }
