"""
Main defect injector for ViDEC-Inspect.

Coordinates crack, spalling, and hard negative generation.
Handles defect placement, overlap prevention, and difficulty balancing.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from .crack_generator import CrackGenerator
from .spall_generator import SpallGenerator
from .negatives_generator import HardNegativeGenerator


class DefectInjector:
    """Main defect injection coordinator."""
    
    def __init__(self):
        """Initialize defect generators."""
        self.crack_gen = CrackGenerator()
        self.spall_gen = SpallGenerator()
        self.negative_gen = HardNegativeGenerator()
    
    def generate_scene(
        self,
        image_size: Tuple[int, int],
        pixel_to_meter: float,
        num_cracks: int = 1,
        num_spalls: int = 1,
        num_negatives: int = 1,
        difficulty_dist: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """
        Generate a complete scene with defects and hard negatives.
        
        Args:
            image_size: (width, height) in pixels
            pixel_to_meter: Conversion factor from pixels to meters
            num_cracks: Number of crack defects
            num_spalls: Number of spalling defects
            num_negatives: Number of hard negatives
            difficulty_dist: Distribution of difficulties, e.g. {"easy": 0.3, "medium": 0.5, "hard": 0.2}
            
        Returns:
            scene_dict: Dictionary containing all defects and negatives
        """
        if difficulty_dist is None:
            difficulty_dist = {"easy": 0.2, "medium": 0.6, "hard": 0.2}
        
        # Generate defects
        cracks = []
        spalls = []
        negatives = []
        
        # Generate cracks
        for i in range(num_cracks):
            difficulty = self._sample_difficulty(difficulty_dist)
            crack = self.crack_gen.generate(
                image_size=image_size,
                pixel_to_meter=pixel_to_meter,
                difficulty=difficulty
            )
            
            # Check for overlap with existing defects
            if not self._check_overlap(crack, cracks + spalls):
                cracks.append(crack)
        
        # Generate spalls
        for i in range(num_spalls):
            difficulty = self._sample_difficulty(difficulty_dist)
            spall = self.spall_gen.generate(
                image_size=image_size,
                pixel_to_meter=pixel_to_meter,
                difficulty=difficulty
            )
            
            # Check for overlap
            if not self._check_overlap(spall, cracks + spalls):
                spalls.append(spall)
        
        # Generate hard negatives
        for i in range(num_negatives):
            difficulty = self._sample_difficulty(difficulty_dist)
            negative = self.negative_gen.generate(
                image_size=image_size,
                pixel_to_meter=pixel_to_meter,
                difficulty=difficulty
            )
            
            # Check for overlap with defects (hard negatives can overlap with each other)
            if not self._check_overlap(negative, cracks + spalls):
                negatives.append(negative)
        
        scene = {
            'num_defects': len(cracks) + len(spalls),
            'num_cracks': len(cracks),
            'num_spalls': len(spalls),
            'num_negatives': len(negatives),
            'cracks': cracks,
            'spalls': spalls,
            'negatives': negatives,
        }
        
        return scene
    
    def _sample_difficulty(self, difficulty_dist: Dict[str, float]) -> str:
        """Sample difficulty level from distribution."""
        difficulties = list(difficulty_dist.keys())
        probs = list(difficulty_dist.values())
        probs = np.array(probs) / np.sum(probs)  # Normalize
        return np.random.choice(difficulties, p=probs)
    
    def _check_overlap(
        self,
        new_defect: Dict,
        existing_defects: List[Dict],
        iou_threshold: float = 0.1
    ) -> bool:
        """
        Check if new defect overlaps significantly with existing defects.
        
        Args:
            new_defect: New defect dictionary with 'bbox_xyxy'
            existing_defects: List of existing defect dictionaries
            iou_threshold: IoU threshold for considering overlap
            
        Returns:
            has_overlap: True if overlap exceeds threshold
        """
        if not existing_defects:
            return False
        
        new_bbox = new_defect['bbox_xyxy']
        
        for existing in existing_defects:
            existing_bbox = existing['bbox_xyxy']
            iou = self._compute_iou(new_bbox, existing_bbox)
            
            if iou > iou_threshold:
                return True
        
        return False
    
    def _compute_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        """
        Compute IoU between two bounding boxes.
        
        Args:
            bbox1: [x_min, y_min, x_max, y_max]
            bbox2: [x_min, y_min, x_max, y_max]
            
        Returns:
            iou: Intersection over Union
        """
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        # Compute intersection
        x_inter_min = max(x1_min, x2_min)
        y_inter_min = max(y1_min, y2_min)
        x_inter_max = min(x1_max, x2_max)
        y_inter_max = min(y1_max, y2_max)
        
        if x_inter_max < x_inter_min or y_inter_max < y_inter_min:
            return 0.0
        
        inter_area = (x_inter_max - x_inter_min) * (y_inter_max - y_inter_min)
        
        # Compute union
        area1 = (x1_max - x1_min) * (y1_max - y1_min)
        area2 = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = area1 + area2 - inter_area
        
        if union_area == 0:
            return 0.0
        
        iou = inter_area / union_area
        return iou
    
    def composite_defects_on_image(
        self,
        base_image: np.ndarray,
        scene: Dict,
        blend_mode: str = "darken"
    ) -> np.ndarray:
        """
        Composite defects onto base image.
        
        Args:
            base_image: Base RGB image (H, W, 3), uint8
            scene: Scene dictionary from generate_scene()
            blend_mode: "darken", "lighten", or "multiply"
            
        Returns:
            composited: Image with defects rendered
        """
        result = base_image.copy()
        
        # Composite cracks (darken)
        for crack in scene['cracks']:
            mask = crack['mask']
            intensity = 0.7  # Darken by 30%
            mask_3ch = np.stack([mask] * 3, axis=-1) / 255.0
            result = (result * (1 - mask_3ch * (1 - intensity))).astype(np.uint8)
        
        # Composite spalls (lighten slightly, add texture)
        for spall in scene['spalls']:
            mask = spall['mask']
            intensity = 1.2  # Lighten by 20%
            mask_3ch = np.stack([mask] * 3, axis=-1) / 255.0
            result = np.clip(result * (1 + mask_3ch * (intensity - 1)), 0, 255).astype(np.uint8)
        
        # Composite hard negatives (varied effects)
        for negative in scene['negatives']:
            mask = negative['mask']
            neg_type = negative['type']
            
            if neg_type == "stain":
                intensity = 0.75
                mask_3ch = np.stack([mask] * 3, axis=-1) / 255.0
                result = (result * (1 - mask_3ch * (1 - intensity))).astype(np.uint8)
            elif neg_type in ["shadow", "texture_variation"]:
                intensity = 0.8
                mask_3ch = np.stack([mask] * 3, axis=-1) / 255.0
                result = (result * (1 - mask_3ch * (1 - intensity))).astype(np.uint8)
        
        return result
