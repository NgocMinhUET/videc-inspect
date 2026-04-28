"""
HoloOcean-backed flat-wall source for ViDEC-Inspect.

This is a skeleton implementation.
It is intentionally conservative and may require adaptation to your exact
HoloOcean version, world, sockets, and control workflow.
"""

from __future__ import annotations

from typing import Optional, Dict, Any

import numpy as np

from .frame_source import FrameSource, CapturePose, CaptureConditions, CaptureResult


class HoloOceanFlatWallSource(FrameSource):
    def __init__(
        self,
        scenario_cfg: Dict[str, Any],
        show_viewport: bool = False,
        disable_viewport_rendering: bool = True,
        warmup_steps: int = 10,
    ):
        self.scenario_cfg = scenario_cfg
        self.show_viewport = show_viewport
        self.disable_viewport_rendering = disable_viewport_rendering
        self.warmup_steps = warmup_steps
        self.env = None

    def _ensure_env(self) -> None:
        if self.env is not None:
            return

        import holoocean  # local import so placeholder mode does not require it

        self.env = holoocean.make(
            scenario_cfg=self.scenario_cfg,
            show_viewport=self.show_viewport,
        )

        if self.disable_viewport_rendering:
            self.env.should_render_viewport(False)

        zero_u = np.zeros(8, dtype=np.float32)
        for _ in range(self.warmup_steps):
            self.env.step(zero_u)

    def _step_to_observation(
        self,
        pose: CapturePose,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Skeleton method.

        You will likely need to replace this logic depending on how you want to:
        - move the vehicle to the desired pose
        - set an exact simulator state
        - or drive the agent close enough to the target wall

        For now, we only do a zero-input step and read the current state.
        """
        if seed is not None:
            np.random.seed(seed)

        zero_u = np.zeros(8, dtype=np.float32)
        state = self.env.step(zero_u)
        return state

    def capture(
        self,
        pose: CapturePose,
        conditions: CaptureConditions,
        seed: Optional[int] = None,
    ) -> CaptureResult:
        self._ensure_env()

        state = self._step_to_observation(pose=pose, seed=seed)

        if "FrontRGB" not in state:
            raise KeyError("HoloOcean state does not contain 'FrontRGB'.")

        if "FrontDepth" not in state:
            raise KeyError("HoloOcean state does not contain 'FrontDepth'.")

        rgb = state["FrontRGB"]
        depth_payload = state["FrontDepth"]

        if not isinstance(depth_payload, dict):
            raise TypeError("Expected FrontDepth payload to be a dict.")

        if "depth" not in depth_payload:
            raise KeyError("FrontDepth payload does not contain raw 'depth'.")

        depth = depth_payload["depth"]

        # Approximate pixel_to_meter from camera geometry if needed.
        # You can refine this later using camera intrinsics or HoloOcean metadata.
        height, width = depth.shape
        fov_deg = 90.0
        fov_rad = np.deg2rad(fov_deg)
        frame_width_m = 2 * pose.standoff_distance_m * np.tan(fov_rad / 2)
        pixel_to_meter = frame_width_m / width

        robot_state = {
            "position_m": [pose.x_m, pose.y_m, pose.z_m],
            "orientation_deg": [pose.roll_deg, pose.pitch_deg, pose.yaw_deg],
            "velocity_m_s": [0.0, 0.0, 0.0],  # replace when Pose/DVL/Velocity available
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
            source_name="holoocean_flat_wall",
            extra={
                "conditions": {
                    "water_clarity": conditions.water_clarity,
                    "lighting": conditions.lighting,
                    "visibility_m": conditions.visibility_m,
                    "artificial_light": conditions.artificial_light,
                    "ambient_illumination_lux": conditions.ambient_illumination_lux,
                },
                "state_keys": list(state.keys()),
            },
        )

    def close(self) -> None:
        if self.env is None:
            return

        try:
            if hasattr(self.env, "close") and callable(self.env.close):
                self.env.close()
            elif hasattr(self.env, "__exit__") and callable(self.env.__exit__):
                self.env.__exit__(None, None, None)
        finally:
            self.env = None
