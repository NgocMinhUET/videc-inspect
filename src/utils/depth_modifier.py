"""
Depth map modification utilities for defect rendering.

Applies geometric modifications to depth maps for defects with 3D structure,
particularly spalling/delamination.
"""

import numpy as np
import cv2
from typing import List, Dict


def apply_spall_to_depth_map(
    depth_map: np.ndarray,
    spalls: List[Dict],
    pixel_to_meter: float,
) -> np.ndarray:
    """
    Apply spalling depth modifications to depth map.
    
    Spalling creates depressions in the surface, which should be visible
    in the depth sensor data.
    
    Args:
        depth_map: Original depth map (H, W) in meters
        spalls: List of spall defect dictionaries with:
            - mask: Binary mask (H, W)
            - depth_mm: Spall depth in millimeters
        pixel_to_meter: Conversion factor
        
    Returns:
        modified_depth: Depth map with spall depressions added
    """
    result = depth_map.copy()
    
    for spall in spalls:
        mask = spall.get('mask')
        spall_depth_mm = spall.get('depth_mm', 0)
        
        if mask is None or spall_depth_mm == 0:
            continue
        
        # Convert spall depth to meters
        spall_depth_m = spall_depth_mm / 1000.0
        
        # Create smooth depression profile
        # Spalling is typically conical or bowl-shaped
        mask_float = mask.astype(np.float32) / 255.0
        
        # Apply Gaussian blur to create smooth depth transition
        kernel_size = int(np.sqrt(np.sum(mask > 0)) / 5)
        kernel_size = max(5, kernel_size)
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        mask_smooth = cv2.GaussianBlur(mask_float, (kernel_size, kernel_size), 0)
        
        # Maximum depression at center, tapering to edges
        # Depression increases depth (object is further away)
        depth_modification = mask_smooth * spall_depth_m
        
        result += depth_modification
    
    return result


def apply_crack_to_depth_map(
    depth_map: np.ndarray,
    cracks: List[Dict],
    pixel_to_meter: float,
) -> np.ndarray:
    """
    Apply crack depth modifications to depth map.
    
    Cracks are typically surface phenomena with minimal depth change,
    but for deep cracks, a small depth discontinuity can be added.
    
    Args:
        depth_map: Original depth map (H, W) in meters
        cracks: List of crack defect dictionaries
        pixel_to_meter: Conversion factor
        
    Returns:
        modified_depth: Depth map with crack modifications (typically minimal)
    """
    result = depth_map.copy()
    
    # For v0.1, cracks have negligible depth effect
    # This is a placeholder for future enhancement
    
    for crack in cracks:
        mean_width_mm = crack.get('mean_width_mm', 0)
        
        # Only very wide cracks (>3mm) have measurable depth
        if mean_width_mm > 3.0:
            mask = crack.get('mask')
            if mask is not None:
                # Very small depth change (0.1 - 0.5mm)
                crack_depth_m = np.random.uniform(0.0001, 0.0005)
                mask_float = mask.astype(np.float32) / 255.0
                result += mask_float * crack_depth_m
    
    return result


def compute_depth_quality_metrics(
    depth_map: np.ndarray,
    robot_distance: float,
) -> Dict:
    """
    Compute depth map quality metrics for verification layer.
    
    Args:
        depth_map: Depth map in meters (H, W)
        robot_distance: Expected distance to wall in meters
        
    Returns:
        quality_metrics: Dictionary with depth quality measures
    """
    valid_mask = np.isfinite(depth_map) & (depth_map > 0)
    
    if not np.any(valid_mask):
        return {
            'mean_depth_m': 0.0,
            'depth_std_m': 0.0,
            'valid_ratio': 0.0,
            'depth_consistency_score': 0.0,
        }
    
    valid_depths = depth_map[valid_mask]
    
    mean_depth = np.mean(valid_depths)
    depth_std = np.std(valid_depths)
    valid_ratio = np.sum(valid_mask) / depth_map.size
    
    # Depth consistency: how close is mean to expected distance
    depth_error = abs(mean_depth - robot_distance)
    depth_consistency = max(0.0, 1.0 - depth_error / robot_distance)
    
    return {
        'mean_depth_m': float(mean_depth),
        'depth_std_m': float(depth_std),
        'valid_ratio': float(valid_ratio),
        'depth_consistency_score': float(depth_consistency),
    }
