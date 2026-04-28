"""
Crack defect generator for ViDEC-Inspect.

Generates synthetic crack defects with:
- Polyline skeletons
- Width profiles
- Optional branching
- Realistic appearance
"""

import numpy as np
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from scipy.interpolate import interp1d
from skimage.draw import line_aa
import cv2


class CrackGenerator:
    """Generate synthetic crack defects."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize crack generator.
        
        Args:
            config_path: Path to crack.yaml config file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "configs" / "defects" / "crack.yaml"
        
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
        Generate a single crack defect.
        
        Args:
            image_size: (width, height) in pixels
            pixel_to_meter: Conversion factor from pixels to meters
            difficulty: "easy", "medium", or "hard"
            severity: "minor", "moderate", or "severe" (auto if None)
            
        Returns:
            defect_dict: Dictionary with all crack attributes
        """
        width, height = image_size
        
        # Get difficulty parameters
        diff_params = self.config['difficulty'][difficulty]
        
        # Sample crack length
        min_len = max(
            self.config['generation']['min_length_m'],
            diff_params.get('min_length_m', 0.05)
        )
        max_len = self.config['generation']['max_length_m']
        length_m = np.random.uniform(min_len, max_len)
        length_px = length_m / pixel_to_meter
        
        # Sample crack width
        if severity:
            severity_params = self.config['severity'][severity]
            min_width = severity_params.get('min_width_mm', self.config['generation']['min_width_mm'])
            max_width = severity_params.get('max_width_mm', self.config['generation']['max_width_mm'])
        else:
            min_width = max(
                self.config['generation']['min_width_mm'],
                diff_params.get('min_width_mm', 0.5)
            )
            max_width = self.config['generation']['max_width_mm']
        
        mean_width_mm = np.random.uniform(min_width, max_width)
        
        # Determine actual severity based on width
        if mean_width_mm < 1.0:
            severity = "minor"
        elif mean_width_mm < 4.0:
            severity = "moderate"
        else:
            severity = "severe"
        
        # Generate skeleton (polyline)
        skeleton_px = self._generate_skeleton(
            image_size=image_size,
            length_px=length_px,
            branching_prob=self.config['generation']['topology']['branching_probability']
        )
        
        # Generate width profile
        num_points = len(skeleton_px)
        width_profile_mm = self._generate_width_profile(
            num_points=num_points,
            mean_width_mm=mean_width_mm,
            variation_std_ratio=self.config['generation']['width_variation']['std_ratio']
        )
        
        # Convert width to pixels for mask generation
        width_profile_px = np.array(width_profile_mm) / (pixel_to_meter * 1000)
        
        # Generate mask
        mask = self._render_crack_mask(
            image_size=image_size,
            skeleton_px=skeleton_px,
            width_profile_px=width_profile_px
        )
        
        # Calculate bounding box
        bbox_xyxy = self._compute_bbox(mask)
        
        # Generate defect ID
        defect_id = f"crack_{self._defect_counter:04d}"
        self._defect_counter += 1
        
        # Build defect dictionary
        defect = {
            'defect_id': defect_id,
            'class': 'crack',
            'severity': severity,
            'difficulty': difficulty,
            
            # Detection layer
            'bbox_xyxy': bbox_xyxy,
            'mask': mask,
            'mask_area_pixels': int(np.sum(mask > 0)),
            
            # Geometry layer
            'skeleton_px': skeleton_px,
            'length_px': float(self._compute_skeleton_length(skeleton_px)),
            
            # Metrology layer
            'length_m': length_m,
            'width_profile_mm': width_profile_mm,
            'mean_width_mm': float(mean_width_mm),
            'max_width_mm': float(np.max(width_profile_mm)),
            'width_std_mm': float(np.std(width_profile_mm)),
            
            # Verification layer
            'minimal_evidence_level': 'roi_plus_skeleton',
            'requires_closeup': True,
        }
        
        return defect
    
    def _generate_skeleton(
        self,
        image_size: Tuple[int, int],
        length_px: float,
        branching_prob: float = 0.2
    ) -> List[Tuple[int, int]]:
        """
        Generate polyline skeleton for crack.
        
        Args:
            image_size: (width, height) in pixels
            length_px: Target crack length in pixels
            branching_prob: Probability of branching (not implemented yet)
            
        Returns:
            skeleton: List of (x, y) coordinates in pixels
        """
        width, height = image_size
        
        # Random starting point (avoid edges)
        margin = 50
        start_x = np.random.randint(margin, width - margin)
        start_y = np.random.randint(margin, height - margin)
        
        # Random initial direction
        angle = np.random.uniform(0, 2 * np.pi)
        
        # Generate polyline segments
        skeleton = [(start_x, start_y)]
        current_x, current_y = start_x, start_y
        remaining_length = length_px
        
        num_segments = np.random.randint(4, 10)
        segment_length = length_px / num_segments
        
        for i in range(num_segments):
            # Vary angle slightly for natural look
            angle += np.random.uniform(-0.3, 0.3)
            
            # Calculate next point
            dx = segment_length * np.cos(angle)
            dy = segment_length * np.sin(angle)
            
            next_x = int(current_x + dx)
            next_y = int(current_y + dy)
            
            # Clamp to image bounds
            next_x = np.clip(next_x, margin, width - margin)
            next_y = np.clip(next_y, margin, height - margin)
            
            skeleton.append((next_x, next_y))
            
            current_x, current_y = next_x, next_y
        
        return skeleton
    
    def _generate_width_profile(
        self,
        num_points: int,
        mean_width_mm: float,
        variation_std_ratio: float = 0.15
    ) -> np.ndarray:
        """
        Generate width profile along crack.
        
        Args:
            num_points: Number of points in skeleton
            mean_width_mm: Mean crack width in millimeters
            variation_std_ratio: Std deviation / mean ratio
            
        Returns:
            width_profile: Array of widths in millimeters
        """
        std_mm = mean_width_mm * variation_std_ratio
        
        # Generate smooth varying width using low-freq noise
        t = np.linspace(0, 1, num_points)
        
        # Base variation (low frequency)
        base = np.sin(t * np.pi * np.random.uniform(1, 3))
        
        # Add small high-freq noise
        noise = np.random.randn(num_points) * 0.3
        
        # Combine and scale
        variation = (base + noise) * std_mm
        width_profile = mean_width_mm + variation
        
        # Ensure positive width
        width_profile = np.maximum(width_profile, 0.1)
        
        return width_profile
    
    def _render_crack_mask(
        self,
        image_size: Tuple[int, int],
        skeleton_px: List[Tuple[int, int]],
        width_profile_px: np.ndarray
    ) -> np.ndarray:
        """
        Render crack as binary mask.
        
        Args:
            image_size: (width, height) in pixels
            skeleton_px: Skeleton polyline
            width_profile_px: Width at each skeleton point in pixels
            
        Returns:
            mask: Binary mask (uint8, 0 or 255)
        """
        width, height = image_size
        mask = np.zeros((height, width), dtype=np.uint8)
        
        # Draw crack segments
        for i in range(len(skeleton_px) - 1):
            x0, y0 = skeleton_px[i]
            x1, y1 = skeleton_px[i + 1]
            
            # Average width for this segment
            w = (width_profile_px[i] + width_profile_px[i + 1]) / 2
            w = max(1, int(w))
            
            # Draw line with anti-aliasing
            cv2.line(mask, (x0, y0), (x1, y1), 255, thickness=w, lineType=cv2.LINE_AA)
        
        return mask
    
    def _compute_skeleton_length(self, skeleton_px: List[Tuple[int, int]]) -> float:
        """Compute total length of skeleton polyline."""
        length = 0.0
        for i in range(len(skeleton_px) - 1):
            x0, y0 = skeleton_px[i]
            x1, y1 = skeleton_px[i + 1]
            length += np.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
        return length
    
    def _compute_bbox(self, mask: np.ndarray) -> List[int]:
        """Compute bounding box from mask."""
        coords = np.column_stack(np.where(mask > 0))
        if len(coords) == 0:
            return [0, 0, 0, 0]
        
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        
        return [int(x_min), int(y_min), int(x_max), int(y_max)]
