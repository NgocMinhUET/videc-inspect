"""
Structural material / surface model for ViDEC-Inspect v0.2.

Generates a concrete-like RGB background using multiscale band-limited noise
(an fBm-style construction), plus mild low-frequency staining and optional
subtle biofouling. Deterministic given seed. Replaces the v0.1 "uniform fill
+ random circles" background with a more inspection-relevant substrate.
"""

from __future__ import annotations

from typing import Optional, Tuple

import cv2
import numpy as np


def _fbm_noise(
    shape: Tuple[int, int],
    octaves: int,
    persistence: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Multi-octave band-limited noise via successive upsampling.

    Returns an HxW float32 field normalized to [0, 1].
    """
    H, W = shape
    result = np.zeros((H, W), dtype=np.float32)
    amplitude = 1.0
    total = 0.0
    base_h = max(4, H // (2 ** octaves))
    base_w = max(4, W // (2 ** octaves))
    for o in range(octaves):
        scale = 2 ** o
        n_h = max(4, base_h * scale)
        n_w = max(4, base_w * scale)
        noise = rng.standard_normal((n_h, n_w)).astype(np.float32)
        noise = cv2.resize(noise, (W, H), interpolation=cv2.INTER_CUBIC)
        result += amplitude * noise
        total += amplitude
        amplitude *= persistence
    result = result / max(total, 1e-6)
    rmin = float(result.min())
    rmax = float(result.max())
    if rmax - rmin > 1e-6:
        result = (result - rmin) / (rmax - rmin)
    else:
        result = np.zeros_like(result)
    return result


def generate_concrete_surface(
    height: int,
    width: int,
    roughness: float = 0.6,
    stain_level: float = 0.3,
    seed: Optional[int] = None,
) -> np.ndarray:
    """Generate a concrete-like RGB background.

    Args:
        height, width: image size in pixels.
        roughness: 0..1, micro-texture amplitude.
        stain_level: 0..1, low-frequency stain bias strength.
        seed: integer seed for reproducibility.

    Returns:
        rgb: HxWx3 uint8 RGB image.
    """
    rng = np.random.default_rng(seed)

    base_gray = float(rng.uniform(0.42, 0.58))
    base_hue_shift = rng.uniform(-0.04, 0.04, size=3).astype(np.float32)

    micro = _fbm_noise((height, width), octaves=4, persistence=0.55, rng=rng)
    macro = _fbm_noise((height, width), octaves=2, persistence=0.70, rng=rng)
    aggregate = _fbm_noise((height, width), octaves=5, persistence=0.45, rng=rng)

    luminance = (
        base_gray
        + (macro - 0.5) * 0.18
        + (micro - 0.5) * 0.08 * float(roughness)
        + (aggregate - 0.5) * 0.06 * float(roughness)
    ).astype(np.float32)
    luminance = np.clip(luminance, 0.0, 1.0)

    rgb = np.stack([luminance + base_hue_shift[i] for i in range(3)], axis=-1)

    if stain_level > 0:
        stain_field = _fbm_noise((height, width), octaves=3, persistence=0.65, rng=rng)
        stain_color = np.array([0.55, 0.45, 0.35], dtype=np.float32)  # warm rust/leaching
        stain_mask = (stain_field > 0.62).astype(np.float32) * float(stain_level)
        stain_mask = cv2.GaussianBlur(stain_mask, (0, 0), sigmaX=12.0)
        sm = stain_mask[..., None]
        rgb = rgb * (1.0 - 0.35 * sm) + stain_color[None, None, :] * 0.35 * sm

    rgb = np.clip(rgb, 0.0, 1.0)
    return (rgb * 255.0).astype(np.uint8)


def add_surface_roughness(
    rgb: np.ndarray,
    strength: float = 0.05,
    seed: Optional[int] = None,
) -> np.ndarray:
    """Add per-pixel luminance perturbation to mimic surface micro-roughness."""
    rng = np.random.default_rng(seed)
    H, W = rgb.shape[:2]
    noise = rng.normal(0.0, float(strength), size=(H, W, 1)).astype(np.float32)
    out = rgb[..., :3].astype(np.float32) / 255.0 + noise
    return (np.clip(out, 0.0, 1.0) * 255.0).astype(np.uint8)


def add_subtle_biofouling(
    rgb: np.ndarray,
    coverage: float = 0.05,
    seed: Optional[int] = None,
) -> np.ndarray:
    """Add subtle green-brown biofouling patches.

    Args:
        rgb: HxWx3 uint8 input.
        coverage: target fraction of pixels in [0,1].
        seed: integer seed.
    """
    rng = np.random.default_rng(seed)
    H, W = rgb.shape[:2]
    field = _fbm_noise((H, W), octaves=4, persistence=0.55, rng=rng)
    threshold = float(np.quantile(field, 1.0 - float(np.clip(coverage, 0.0, 1.0))))
    mask = (field > threshold).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=6.0)
    tint = np.array([0.30, 0.45, 0.25], dtype=np.float32)  # green-brown
    rgb_f = rgb[..., :3].astype(np.float32) / 255.0
    m3 = mask[..., None]
    out = rgb_f * (1.0 - 0.45 * m3) + tint[None, None, :] * 0.45 * m3
    return (np.clip(out, 0.0, 1.0) * 255.0).astype(np.uint8)
