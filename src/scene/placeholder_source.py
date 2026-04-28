"""
Placeholder synthetic flat-wall source for ViDEC-Inspect.

This wraps the current placeholder generation logic behind the FrameSource API.
"""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from .frame_source import FrameSource, CapturePose, CaptureConditions, CaptureResult
from ..utils.config import benchmark_config


class PlaceholderFlatWallSource(FrameSource):
    def __init__(self, frame_size=(1920, 1080)):
        self.frame_size = frame_size

    def capture(
        self,
        pose: CapturePose,
        conditions: CaptureConditions,
        seed: Optional[int] = None,
    ) -> CaptureResult:
        if seed is not None:
            np.random.seed(seed)

        width, height = self.frame_size

        # RGB placeholder texture
        base_color = np.random.randint(100, 140)
        rgb = np.full((height, width, 3), base_color, dtype=np.uint8)

        noise = np.random.randn(height, width, 3) * 15
        rgb = np.clip(rgb + noise, 0, 255).astype(np.uint8)

        for _ in range(3):
            cx = np.random.randint(0, width)
            cy = np.random.randint(0, height)
            radius = np.random.randint(50, 200)
            cv2.circle(
                rgb,
                (cx, cy),
                radius,
                tuple(np.random.randint(90, 150, 3).tolist()),
                -1,
            )

        rgb = cv2.GaussianBlur(rgb, (5, 5), 0)

        # Flat wall depth
        depth = np.full((height, width), pose.standoff_distance_m, dtype=np.float32)
        depth += np.random.randn(height, width) * 0.005

        if abs(pose.view_angle_deg) > 5:
            angle_rad = np.deg2rad(pose.view_angle_deg)
            x_coords = np.linspace(-1, 1, width)
            depth_variation = (
                x_coords * pose.standoff_distance_m * np.tan(angle_rad) * 0.5
            )
            depth += depth_variation[np.newaxis, :]

        # Pixel-to-meter conversion
        fov_rad = np.deg2rad(benchmark_config.get_camera_params()["fov_deg"])
        frame_width_m = 2 * pose.standoff_distance_m * np.tan(fov_rad / 2)
        pixel_to_meter = frame_width_m / width

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
            source_name="placeholder_flat_wall",
            extra={
                "conditions": {
                    "water_clarity": conditions.water_clarity,
                    "lighting": conditions.lighting,
                    "visibility_m": conditions.visibility_m,
                    "artificial_light": conditions.artificial_light,
                    "ambient_illumination_lux": conditions.ambient_illumination_lux,
                }
            },
        )
