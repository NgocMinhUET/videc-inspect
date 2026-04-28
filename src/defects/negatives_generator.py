"""
Hard negative generator for ViDEC-Inspect.

Generates non-defect patterns designed to test false positive rates:
- Stains (look like cracks)
- Shadows (look like spalling)
- Texture variations
- Biological growth
- Surface artifacts
"""

import numpy as np
import yaml
import cv2
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class HardNegativeGenerator:
    """Generate hard negative samples."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize hard negative generator.
        
        Args:
            config_path: Path to hard_negative.yaml config file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "configs" / "defects" / "hard_negative.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self._negative_counter = 0
    
    def generate(
        self,
        image_size: Tuple[int, int],
        pixel_to_meter: float,
        negative_type: Optional[str] = None,
        difficulty: str = "medium",
    ) -> Dict:
        """
        Generate a single hard negative.
        
        Args:
            image_size: (width, height) in pixels
            pixel_to_meter: Conversion factor from pixels to meters
            negative_type: Type of negative ("stain", "shadow", etc.) or None for random
            difficulty: "easy", "medium", or "hard"
            
        Returns:
            negative_dict: Dictionary with hard negative attributes
        """
        # Select negative type if not specified
        if negative_type is None:
            negative_type = self._sample_negative_type()
        
        # Generate based on type
        if negative_type == "stain":
            negative = self._generate_stain(image_size, pixel_to_meter, difficulty)
        elif negative_type == "shadow":
            negative = self._generate_shadow(image_size, pixel_to_meter, difficulty)
        elif negative_type == "texture_variation":
            negative = self._generate_texture(image_size, pixel_to_meter, difficulty)
        elif negative_type == "biological_growth":
            negative = self._generate_biological(image_size, pixel_to_meter, difficulty)
        elif negative_type == "surface_artifact":
            negative = self._generate_artifact(image_size, pixel_to_meter, difficulty)
        else:
            raise ValueError(f"Unknown negative type: {negative_type}")
        
        # Add common fields
        negative['negative_id'] = f"neg_{self._negative_counter:04d}"
        negative['type'] = negative_type
        negative['difficulty'] = difficulty
        self._negative_counter += 1
        
        return negative
    
    def _sample_negative_type(self) -> str:
        """Sample negative type based on distribution."""
        types = list(self.config['distribution'].keys())
        probs = list(self.config['distribution'].values())
        probs = np.array(probs) / np.sum(probs)  # Normalize
        return np.random.choice(types, p=probs)
    
    def _generate_stain(
        self,
        image_size: Tuple[int, int],
        pixel_to_meter: float,
        difficulty: str
    ) -> Dict:
        """Generate stain pattern (confusable with crack)."""
        width, height = image_size
        config = self.config['types']['stain']
        
        # Sample dimensions
        aspect_ratio = np.random.uniform(*config['generation']['aspect_ratio'])
        width_m = np.random.uniform(*config['generation']['width_m'])
        length_m = np.random.uniform(*config['generation']['length_m'])
        
        width_px = width_m / pixel_to_meter
        length_px = length_m / pixel_to_meter
        
        # Random position
        margin = 50
        center_x = np.random.randint(margin, width - margin)
        center_y = np.random.randint(margin, height - margin)
        
        # Random orientation
        angle = np.random.uniform(0, 2 * np.pi)
        
        # Create elongated blob mask
        mask = np.zeros((height, width), dtype=np.uint8)
        
        # Draw ellipse
        axes = (int(length_px / 2), int(width_px / 2))
        cv2.ellipse(
            mask,
            center=(center_x, center_y),
            axes=axes,
            angle=np.rad2deg(angle),
            startAngle=0,
            endAngle=360,
            color=255,
            thickness=-1
        )
        
        # Add fuzzy edges if specified
        if config['generation']['color_shift'].get('fuzzy_edges', False):
            mask = cv2.GaussianBlur(mask, (9, 9), 2.0)
            mask = (mask > 128).astype(np.uint8) * 255
        
        # Compute bbox
        bbox_xyxy = self._compute_bbox(mask)
        
        return {
            'bbox_xyxy': bbox_xyxy,
            'mask': mask,
            'confusable_with': config['confusable_with'],
            'distinguishing_feature': config['distinguishing_feature'],
            'should_reject': True,
        }
    
    def _generate_shadow(
        self,
        image_size: Tuple[int, int],
        pixel_to_meter: float,
        difficulty: str
    ) -> Dict:
        """Generate shadow pattern (confusable with spalling)."""
        width, height = image_size
        config = self.config['types']['shadow']
        
        # Sample area
        area_m2 = np.random.uniform(*config['generation']['area_m2'])
        area_px2 = area_m2 / (pixel_to_meter ** 2)
        radius_px = np.sqrt(area_px2 / np.pi)
        
        # Random position
        margin = 100
        center_x = np.random.randint(margin, width - margin)
        center_y = np.random.randint(margin, height - margin)
        
        # Create irregular polygon
        num_vertices = np.random.randint(5, 10)
        angles = np.linspace(0, 2 * np.pi, num_vertices, endpoint=False)
        
        contour = []
        for angle in angles:
            r = radius_px * np.random.uniform(0.7, 1.3)
            x = int(center_x + r * np.cos(angle))
            y = int(center_y + r * np.sin(angle))
            contour.append((x, y))
        
        # Render mask
        mask = np.zeros((height, width), dtype=np.uint8)
        contour_array = np.array(contour, dtype=np.int32)
        cv2.fillPoly(mask, [contour_array], 255)
        
        # Compute bbox
        bbox_xyxy = self._compute_bbox(mask)
        
        return {
            'bbox_xyxy': bbox_xyxy,
            'mask': mask,
            'confusable_with': config['confusable_with'],
            'distinguishing_feature': config['distinguishing_feature'],
            'should_reject': True,
        }
    
    def _generate_texture(
        self,
        image_size: Tuple[int, int],
        pixel_to_meter: float,
        difficulty: str
    ) -> Dict:
        """Generate texture variation (confusable with spalling)."""
        width, height = image_size
        config = self.config['types']['texture_variation']
        
        # Sample area
        area_m2 = np.random.uniform(*config['generation']['area_m2'])
        area_px2 = area_m2 / (pixel_to_meter ** 2)
        radius_px = np.sqrt(area_px2 / np.pi)
        
        # Random position
        margin = 80
        center_x = np.random.randint(margin, width - margin)
        center_y = np.random.randint(margin, height - margin)
        
        # Create organic blob
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.circle(mask, (center_x, center_y), int(radius_px), 255, -1)
        
        # Add irregular boundary
        mask = cv2.GaussianBlur(mask, (15, 15), 3.0)
        mask = (mask > 100).astype(np.uint8) * 255
        
        # Compute bbox
        bbox_xyxy = self._compute_bbox(mask)
        
        return {
            'bbox_xyxy': bbox_xyxy,
            'mask': mask,
            'confusable_with': config['confusable_with'],
            'distinguishing_feature': config['distinguishing_feature'],
            'should_reject': True,
        }
    
    def _generate_biological(
        self,
        image_size: Tuple[int, int],
        pixel_to_meter: float,
        difficulty: str
    ) -> Dict:
        """Generate biological growth pattern."""
        width, height = image_size
        config = self.config['types']['biological_growth']
        
        # Sample area
        area_m2 = np.random.uniform(*config['generation']['area_m2'])
        area_px2 = area_m2 / (pixel_to_meter ** 2)
        radius_px = np.sqrt(area_px2 / np.pi)
        
        # Random position
        margin = 80
        center_x = np.random.randint(margin, width - margin)
        center_y = np.random.randint(margin, height - margin)
        
        # Create fuzzy organic blob
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.circle(mask, (center_x, center_y), int(radius_px), 255, -1)
        
        # Heavy blur for organic look
        mask = cv2.GaussianBlur(mask, (21, 21), 5.0)
        mask = (mask > 80).astype(np.uint8) * 255
        
        # Compute bbox
        bbox_xyxy = self._compute_bbox(mask)
        
        return {
            'bbox_xyxy': bbox_xyxy,
            'mask': mask,
            'confusable_with': config['confusable_with'],
            'distinguishing_feature': config['distinguishing_feature'],
            'should_reject': True,
        }
    
    def _generate_artifact(
        self,
        image_size: Tuple[int, int],
        pixel_to_meter: float,
        difficulty: str
    ) -> Dict:
        """Generate surface artifact pattern."""
        width, height = image_size
        config = self.config['types']['surface_artifact']
        
        # Sample area
        area_m2 = np.random.uniform(*config['generation']['area_m2'])
        area_px2 = area_m2 / (pixel_to_meter ** 2)
        radius_px = np.sqrt(area_px2 / np.pi)
        
        # Random position
        margin = 70
        center_x = np.random.randint(margin, width - margin)
        center_y = np.random.randint(margin, height - margin)
        
        # Create smooth blob
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.circle(mask, (center_x, center_y), int(radius_px), 255, -1)
        
        # Slight blur for smooth look
        mask = cv2.GaussianBlur(mask, (7, 7), 1.5)
        mask = (mask > 150).astype(np.uint8) * 255
        
        # Compute bbox
        bbox_xyxy = self._compute_bbox(mask)
        
        return {
            'bbox_xyxy': bbox_xyxy,
            'mask': mask,
            'confusable_with': config['confusable_with'],
            'distinguishing_feature': config['distinguishing_feature'],
            'should_reject': True,
        }
    
    def _compute_bbox(self, mask: np.ndarray) -> List[int]:
        """Compute bounding box from mask."""
        coords = np.column_stack(np.where(mask > 0))
        if len(coords) == 0:
            return [0, 0, 0, 0]
        
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        
        return [int(x_min), int(y_min), int(x_max), int(y_max)]
