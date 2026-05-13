"""
Camera and sensor degradation for ViDEC-Inspect v0.2.

Applies, in order: exposure, gain, defocus blur, motion blur, Gaussian + shot
noise approximation, and optional JPEG compression. Deterministic given seed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
import yaml


_DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "configs" / "synthesis" / "camera_model.yaml"
)


def load_camera_model_config(config_path: Optional[str] = None) -> Dict:
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _motion_blur_kernel(size: int, angle_deg: float) -> np.ndarray:
    """Generate a normalized 1-D motion blur kernel rotated by angle_deg."""
    size = max(1, int(size) | 1)  # odd
    k = np.zeros((size, size), dtype=np.float32)
    k[size // 2, :] = 1.0
    M = cv2.getRotationMatrix2D((size / 2 - 0.5, size / 2 - 0.5), angle_deg, 1.0)
    k = cv2.warpAffine(k, M, (size, size))
    s = k.sum()
    return k / s if s > 0 else k


def apply_camera_model(
    rgb: np.ndarray,
    exposure: float = 1.0,
    gain: float = 1.0,
    noise_level: float = 0.01,
    blur_sigma: float = 0.0,
    motion_blur_kernel: int = 0,
    motion_blur_angle_deg: float = 0.0,
    compression_quality: Optional[int] = None,
    seed: Optional[int] = None,
) -> Tuple[np.ndarray, Dict]:
    """Apply sensor-level degradation to an RGB image.

    Args:
        rgb: HxWx3 uint8 RGB image.
        exposure: linear pre-noise gain factor.
        gain: additional linear gain factor (electronics).
        noise_level: Gaussian noise std (in [0,1] image scale).
        blur_sigma: defocus Gaussian blur sigma (px).
        motion_blur_kernel: motion blur kernel size (px); 0 disables.
        motion_blur_angle_deg: motion blur angle (deg).
        compression_quality: JPEG quality in [10, 100] or None to skip.
        seed: integer seed for reproducibility.

    Returns:
        degraded_rgb: HxWx3 uint8 RGB image.
        camera_quality_metrics: dict with applied parameters and quality scores.
    """
    if rgb.ndim != 3 or rgb.shape[2] < 3:
        raise ValueError("rgb must be HxWx3")

    rng = np.random.default_rng(seed)
    I = rgb[..., :3].astype(np.float32) / 255.0
    I = np.clip(I * exposure * gain, 0.0, 1.5)

    if blur_sigma > 0.05:
        I = cv2.GaussianBlur(I, ksize=(0, 0), sigmaX=float(blur_sigma), sigmaY=float(blur_sigma))

    if motion_blur_kernel and motion_blur_kernel >= 3:
        kernel = _motion_blur_kernel(motion_blur_kernel, motion_blur_angle_deg)
        I = cv2.filter2D(I, ddepth=-1, kernel=kernel)

    if noise_level > 0:
        gaussian = rng.normal(0.0, noise_level, size=I.shape).astype(np.float32)
        shot = (rng.normal(0.0, noise_level * 0.5, size=I.shape).astype(np.float32)
                * np.sqrt(np.clip(I, 0.0, 1.0)))
        I = I + gaussian + shot

    I = np.clip(I, 0.0, 1.0)
    degraded = (I * 255.0).astype(np.uint8)

    if compression_quality is not None:
        quality = int(np.clip(compression_quality, 10, 100))
        ok, buf = cv2.imencode(
            ".jpg",
            cv2.cvtColor(degraded, cv2.COLOR_RGB2BGR),
            [int(cv2.IMWRITE_JPEG_QUALITY), quality],
        )
        if ok:
            decoded = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            degraded = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)

    gray = cv2.cvtColor(degraded, cv2.COLOR_RGB2GRAY)
    sharpness_raw = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharpness_score = float(1.0 - np.exp(-sharpness_raw / 500.0))
    contrast_score = float(np.clip(gray.std() / (128.0 * 0.35), 0.0, 1.0))

    metrics = {
        "exposure": float(exposure),
        "gain": float(gain),
        "noise_level": float(noise_level),
        "blur_sigma": float(blur_sigma),
        "motion_blur_kernel": int(motion_blur_kernel),
        "motion_blur_angle_deg": float(motion_blur_angle_deg),
        "compression_quality": int(compression_quality) if compression_quality is not None else None,
        "camera_sharpness_score": sharpness_score,
        "camera_contrast_score": contrast_score,
    }
    return degraded, metrics
