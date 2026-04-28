"""
Spalling defect generator for ViDEC-Inspect.

Generates synthetic spalling defects with:
- Irregular polygon contours
- Depth maps
- Area and volume measurements
"""

import numpy as np
import yaml
import cv2
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from scipy.spatial import ConvexHull
from ..utils.config import benchmark_config


class SpallGenerator:
    """Generate synthetic spalling defects."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize spalling generator.
        
        Args:
            config_path: Path to spall.yaml config file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "configs" / "defects" / "spall.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self._defect_counter = 0
    
    def generate(
        self,
        image_size: Tuple[int, int],
        pixel_to_meter: float,
        difficulty: str = "medium",
        severity: Optional[str] = None,
    ) -> Dict:
        """
        Generate a single spalling defect.
        
        Args:
            image_size: (width, height) in pixels
            pixel_to_meter: Conversion factor from pixels to meters
            difficulty: "easy", "medium", or "hard"
            severity: "minor", "moderate", or "severe" (auto if None)
            
        Returns:
            defect_dict: Dictionary with all spalling attributes
        """
        width, height = image_size
        
        # Get difficulty parameters
        diff_params = self.config['difficulty'][difficulty]
        
        # Sample spalling area
        min_area = max(
            self.config['generation']['min_area_m2'],
            diff_params.get('min_area_m2', 0.001)
        )
        max_area = self.config['generation']['max_area_m2']
        area_m2 = np.random.uniform(min_area, max_area)
        area_px2 = area_m2 / (pixel_to_meter ** 2)
        
        # Sample depth
        if severity:
            severity_params = self.config['severity'][severity]
            min_depth = severity_params.get('min_depth_mm', self.config['generation']['min_depth_mm'])
            max_depth = severity_params.get('max_depth_mm', self.config['generation']['max_depth_mm'])
        else:
            min_depth = max(
                self.config['generation']['min_depth_mm'],
                diff_params.get('min_depth_mm', 2.0)
            )
            max_depth = self.config['generation']['max_depth_mm']
        
        depth_mm = np.random.uniform(min_depth, max_depth)
        
        # Classify severity using centralized config
        severity = benchmark_config.classify_severity("spall", depth_mm)
        
        # Generate contour (irregular polygon)
        contour_px = self._generate_contour(
            image_size=image_size,
            target_area_px2=area_px2,
            irregularity=self.config['generation']['shape']['irregularity']
        )
        
        # Generate mask
        mask = self._render_spall_mask(
            image_size=image_size,
            contour_px=contour_px
        )
        
        # Calculate actual area
        actual_area_px2 = int(np.sum(mask > 0))
        actual_area_m2 = actual_area_px2 * (pixel_to_meter ** 2)
        
        # Calculate volume (assuming conical depression)
        volume_cm3 = (actual_area_m2 * 1e4) * (depth_mm / 10) / 3  # cm³
        
        # Calculate bounding box
        bbox_xyxy = self._compute_bbox(mask)
        
        # Calculate shape properties
        perimeter_px = self._compute_perimeter(contour_px)
        major_axis_deg, minor_axis_ratio = self._compute_axes(contour_px)
        
        # Generate defect ID
        defect_id = f"spall_{self._defect_counter:04d}"
        self._defect_counter += 1
        
        # Build defect dictionary
        # NOTE: Removed verification fields (minimal_evidence_level, requires_closeup)
        # as these should be determined by verification layer based on config
        defect = {
            'defect_id': defect_id,
            'class_name': 'spall',  # Standardized to "spall" not "spalling"
            'class': 'spall',  # Keep for backward compatibility during transition
            'severity': severity,
            'difficulty': difficulty,
            
            # Detection layer
            'bbox_xyxy': bbox_xyxy,
            'mask': mask,
            'mask_area_pixels': actual_area_px2,
            
            # Geometry layer
            'contour_px': contour_px,
            'perimeter_px': float(perimeter_px),
            'major_axis_deg': float(major_axis_deg),
            'minor_axis_ratio': float(minor_axis_ratio),
            
            # Metrology layer
            'area_m2': float(actual_area_m2),
            'depth_mm': float(depth_mm),
            'volume_cm3': float(volume_cm3),
        }
        
        return defect
    
    def _generate_contour(
        self,
        image_size: Tuple[int, int],
        target_area_px2: float,
        irregularity: float = 0.3
    ) -> List[Tuple[int, int]]:
        """
        Generate irregular polygon contour.
        
        Args:
            image_size: (width, height) in pixels
            target_area_px2: Target area in pixels²
            irregularity: 0=circle, 1=very irregular
            
        Returns:
            contour: List of (x, y) coordinates in pixels
        """
        width, height = image_size
        
        # Random center (avoid edges)
        margin = 100
        center_x = np.random.randint(margin, width - margin)
        center_y = np.random.randint(margin, height - margin)
        
        # Estimate radius from target area
        radius_px = np.sqrt(target_area_px2 / np.pi)
        
        # Generate vertices
        num_vertices = np.random.randint(
            self.config['generation']['shape']['num_vertices'][0],
            self.config['generation']['shape']['num_vertices'][1] + 1
        )
        
        angles = np.linspace(0, 2 * np.pi, num_vertices, endpoint=False)
        
        # Add irregularity to radius
        radii = []
        for angle in angles:
            r = radius_px * (1.0 + np.random.uniform(-irregularity, irregularity))
            radii.append(r)
        
        # Generate contour points
        contour = []
        for angle, r in zip(angles, radii):
            x = int(center_x + r * np.cos(angle))
            y = int(center_y + r * np.sin(angle))
            
            # Clamp to image bounds
            x = np.clip(x, margin, width - margin)
            y = np.clip(y, margin, height - margin)
            
            contour.append((x, y))
        
        return contour
    
    def _render_spall_mask(
        self,
        image_size: Tuple[int, int],
        contour_px: List[Tuple[int, int]]
    ) -> np.ndarray:
        """
        Render spalling as binary mask.
        
        Args:
            image_size: (width, height) in pixels
            contour_px: Contour polygon
            
        Returns:
            mask: Binary mask (uint8, 0 or 255)
        """
        width, height = image_size
        mask = np.zeros((height, width), dtype=np.uint8)
        
        # Convert contour to numpy array format for cv2
        contour_array = np.array(contour_px, dtype=np.int32)
        
        # Fill polygon
        cv2.fillPoly(mask, [contour_array], 255)
        
        return mask
    
    def _compute_perimeter(self, contour_px: List[Tuple[int, int]]) -> float:
        """Compute perimeter of contour."""
        perimeter = 0.0
        n = len(contour_px)
        for i in range(n):
            x0, y0 = contour_px[i]
            x1, y1 = contour_px[(i + 1) % n]
            perimeter += np.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
        return perimeter
    
    def _compute_axes(self, contour_px: List[Tuple[int, int]]) -> Tuple[float, float]:
        """
        Compute major axis orientation and minor/major axis ratio.
        
        Returns:
            major_axis_deg: Orientation of major axis in degrees
            minor_axis_ratio: Ratio of minor to major axis
        """
        if len(contour_px) < 5:
            return 0.0, 1.0
        
        # Convert to numpy array
        points = np.array(contour_px, dtype=np.float32)
        
        # Fit ellipse
        try:
            ellipse = cv2.fitEllipse(points)
            (center, axes, angle) = ellipse
            major_axis = max(axes)
            minor_axis = min(axes)
            
            major_axis_deg = angle if axes[0] >= axes[1] else (angle + 90) % 180
            minor_axis_ratio = minor_axis / major_axis if major_axis > 0 else 1.0
            
            return major_axis_deg, minor_axis_ratio
        except:
            # Fallback if ellipse fitting fails
            return 0.0, 1.0
    
    def _compute_bbox(self, mask: np.ndarray) -> List[int]:
        """Compute bounding box from mask."""
        coords = np.column_stack(np.where(mask > 0))
        if len(coords) == 0:
            return [0, 0, 0, 0]
        
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        
        return [int(x_min), int(y_min), int(x_max), int(y_max)]
