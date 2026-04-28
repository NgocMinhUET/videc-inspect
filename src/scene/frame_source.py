"""
Abstract frame source interface for ViDEC-Inspect.

A frame source is responsible for producing one observation
(RGB, depth, metadata) for a given pose and condition set.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class CapturePose:
    """
    Pose and view specification for one capture.
    """
    x_m: float
    y_m: float
    z_m: float
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    standoff_distance_m: float = 1.5
    view_angle_deg: float = 0.0


@dataclass
class CaptureConditions:
    """
    Environmental conditions for one capture.
    """
    water_clarity: str = "moderate"
    lighting: str = "normal"
    visibility_m: float = 8.5
    artificial_light: bool = True
    ambient_illumination_lux: float = 300.0


@dataclass
class CaptureResult:
    """
    Standardized output of any frame source.
    """
    rgb: np.ndarray
    depth: np.ndarray
    pixel_to_meter: float
    robot_state: Dict[str, Any]
    camera_state: Dict[str, Any]
    source_name: str
    extra: Optional[Dict[str, Any]] = None


class FrameSource(ABC):
    """
    Abstract frame source interface.

    All concrete sources should return CaptureResult with the same structure,
    so the dataset generation pipeline does not care whether frames come from:
    - placeholder synthetic rendering
    - HoloOcean
    - another simulator later
    """

    @abstractmethod
    def capture(
        self,
        pose: CapturePose,
        conditions: CaptureConditions,
        seed: Optional[int] = None,
    ) -> CaptureResult:
        raise NotImplementedError

    def close(self) -> None:
        """
        Optional cleanup hook for simulator-backed sources.
        """
        return
