"""
Physics-aware flat-wall source for ViDEC-Inspect v0.2.

Implements the FrameSource interface with the same input/output contract as
PlaceholderFlatWallSource and HoloOceanFlatWallSource. The source returns:

- a concrete-like RGB background (NOT yet attenuated by water optics),
- a metric depth map (flat wall + view-angle tilt + mild noise),
- metadata describing the sampled material, water, and lighting parameters.

The dataset generation pipeline in scripts/generate_dataset_v2.py is
responsible for applying the underwater optics + camera degradation AFTER
defects are composited, which keeps masks/skeletons/contours and depth
modifications strictly consistent (v0.2-lite integration).
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from .frame_source import (
    FrameSource,
    CapturePose,
    CaptureConditions,
    CaptureResult,
)
from ..utils.config import benchmark_config
from ..synthesis.material_model import (
    generate_concrete_surface,
    add_surface_roughness,
    add_subtle_biofouling,
)
from ..synthesis.underwater_optics import load_underwater_optics_config


class PhysicsAwareFlatWallSource(FrameSource):
    """Physics-aware concrete-substrate flat-wall source.

    Notes:
        - Underwater optics are NOT applied inside this source. The
          downstream pipeline applies them after defect compositing, so
          attenuation/backscatter act on the composited (background + defect)
          image while masks/depth remain authoritative ground truth.
        - The source exposes the sampled optics PARAMETERS through `extra`
          so that the pipeline can call apply_underwater_optics with the
          correct (water_type, lighting_level) for this frame.
    """

    def __init__(
        self,
        frame_size=(1920, 1080),
        apply_biofouling_prob: float = 0.35,
    ):
        self.frame_size = frame_size
        self.apply_biofouling_prob = float(apply_biofouling_prob)
        self._optics_cfg = load_underwater_optics_config()

    def capture(
        self,
        pose: CapturePose,
        conditions: CaptureConditions,
        seed: Optional[int] = None,
    ) -> CaptureResult:
        rng = np.random.default_rng(seed)
        width, height = self.frame_size

        # 1. Generate physics-motivated concrete substrate.
        roughness = float(rng.uniform(0.45, 0.85))
        stain_level = float(rng.uniform(0.15, 0.55))
        substrate_seed = None if seed is None else int(seed + 1)
        rgb = generate_concrete_surface(
            height=height,
            width=width,
            roughness=roughness,
            stain_level=stain_level,
            seed=substrate_seed,
        )
        rgb = add_surface_roughness(
            rgb,
            strength=0.02 + 0.04 * roughness,
            seed=None if seed is None else int(seed + 2),
        )
        biofouling_applied = bool(rng.random() < self.apply_biofouling_prob)
        biofouling_coverage = 0.0
        if biofouling_applied:
            biofouling_coverage = float(rng.uniform(0.02, 0.10))
            rgb = add_subtle_biofouling(
                rgb,
                coverage=biofouling_coverage,
                seed=None if seed is None else int(seed + 3),
            )

        # 2. Flat-wall depth map with mild noise and view-angle tilt.
        depth = np.full((height, width), pose.standoff_distance_m, dtype=np.float32)
        depth = depth + rng.normal(0.0, 0.004, size=depth.shape).astype(np.float32)
        if abs(pose.view_angle_deg) > 5:
            angle_rad = float(np.deg2rad(pose.view_angle_deg))
            x_coords = np.linspace(-1.0, 1.0, width, dtype=np.float32)
            depth_variation = (
                x_coords * pose.standoff_distance_m * np.tan(angle_rad) * 0.5
            ).astype(np.float32)
            depth = depth + depth_variation[np.newaxis, :]

        # 3. Pixel-to-meter conversion (same convention as v0.1 placeholder).
        fov_rad = np.deg2rad(benchmark_config.get_camera_params()["fov_deg"])
        frame_width_m = 2 * pose.standoff_distance_m * np.tan(fov_rad / 2)
        pixel_to_meter = float(frame_width_m / width)

        # 4. Resolve water_type from v0.1 condition labels.
        alias = self._optics_cfg.get("clarity_alias", {}) or {}
        water_type = alias.get(conditions.water_clarity, conditions.water_clarity)
        lighting_level = conditions.lighting

        sampled_optics = None
        if water_type in self._optics_cfg.get("water_types", {}):
            w_cfg = self._optics_cfg["water_types"][water_type]
            l_cfg = self._optics_cfg["lighting"].get(
                lighting_level, self._optics_cfg["lighting"]["normal"]
            )
            sampled_optics = {
                "water_type": water_type,
                "lighting_level": lighting_level,
                "beta_rgb_range": w_cfg["beta_rgb"],
                "backscatter_strength_range": w_cfg["backscatter_strength"],
                "blur_sigma_range": w_cfg["blur_sigma"],
                "contrast_scale_range": w_cfg["contrast_scale"],
                "exposure_range": l_cfg["exposure"],
                "noise_level_range": l_cfg["noise_level"],
            }

        robot_state = {
            "position_m": [pose.x_m, pose.y_m, pose.z_m],
            "orientation_deg": [pose.roll_deg, pose.pitch_deg, pose.yaw_deg],
            "velocity_m_s": [0.0, 0.0, 0.0],
        }
        camera_state = {
            "distance_to_wall_m": pose.standoff_distance_m,
            "view_angle_deg": pose.view_angle_deg,
            "look_at_point": [pose.x_m, 0.0, pose.z_m],
        }

        return CaptureResult(
            rgb=rgb,
            depth=depth,
            pixel_to_meter=pixel_to_meter,
            robot_state=robot_state,
            camera_state=camera_state,
            source_name="physics_aware_flat_wall",
            extra={
                "conditions": {
                    "water_clarity": conditions.water_clarity,
                    "lighting": conditions.lighting,
                    "visibility_m": conditions.visibility_m,
                    "artificial_light": conditions.artificial_light,
                    "ambient_illumination_lux": conditions.ambient_illumination_lux,
                },
                "material": {
                    "roughness": roughness,
                    "stain_level": stain_level,
                    "biofouling_applied": biofouling_applied,
                    "biofouling_coverage": biofouling_coverage,
                },
                "water_type": water_type,
                "lighting_level": lighting_level,
                "sampled_optics": sampled_optics,
            },
        )
