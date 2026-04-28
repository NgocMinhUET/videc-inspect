"""Visualization utilities for ViDEC-Inspect."""

import numpy as np
import cv2
from typing import Dict, List, Optional
from pathlib import Path


def visualize_frame(
    rgb_image: np.ndarray,
    depth_map: Optional[np.ndarray],
    defects: List[Dict],
    negatives: List[Dict],
    output_path: Optional[str] = None,
    show_masks: bool = True,
    show_skeletons: bool = True,
) -> np.ndarray:
    """
    Visualize frame with defects and annotations.
    
    Args:
        rgb_image: RGB image (H, W, 3)
        depth_map: Depth map in meters (H, W) or None
        defects: List of defect dictionaries
        negatives: List of hard negative dictionaries
        output_path: Optional path to save visualization
        show_masks: Whether to show segmentation masks
        show_skeletons: Whether to show crack skeletons
        
    Returns:
        vis_image: Visualization image
    """
    vis = rgb_image.copy()
    
    # Draw defects
    for defect in defects:
        color = (0, 255, 0) if defect['class'] == 'crack' else (0, 255, 255)
        
        # Draw bounding box
        bbox = defect['bbox_xyxy']
        cv2.rectangle(vis, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
        
        # Draw label
        label = f"{defect['class']} ({defect['severity']})"
        cv2.putText(
            vis, label, (bbox[0], bbox[1] - 5),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
        )
        
        # Draw mask overlay
        if show_masks and 'mask' in defect:
            mask = defect['mask']
            overlay = np.zeros_like(vis)
            overlay[mask > 0] = color
            vis = cv2.addWeighted(vis, 0.8, overlay, 0.2, 0)
        
        # Draw skeleton for cracks
        if show_skeletons and defect['class'] == 'crack' and 'skeleton_px' in defect:
            skeleton = defect['skeleton_px']
            for i in range(len(skeleton) - 1):
                pt1 = skeleton[i]
                pt2 = skeleton[i + 1]
                cv2.line(vis, pt1, pt2, (255, 0, 0), 2)
    
    # Draw hard negatives
    for negative in negatives:
        color = (255, 0, 0)  # Red for negatives
        
        bbox = negative['bbox_xyxy']
        cv2.rectangle(vis, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
        
        label = f"NEG: {negative['type']}"
        cv2.putText(
            vis, label, (bbox[0], bbox[1] - 5),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1
        )
    
    # Save if requested
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(output_path, cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
    
    return vis


def draw_defects_on_image(
    image: np.ndarray,
    defects: List[Dict],
    show_boxes: bool = True,
    show_masks: bool = True,
    show_labels: bool = True,
) -> np.ndarray:
    """
    Draw defects on image.
    
    Args:
        image: RGB image (H, W, 3)
        defects: List of defect dictionaries
        show_boxes: Whether to show bounding boxes
        show_masks: Whether to show masks
        show_labels: Whether to show labels
        
    Returns:
        annotated: Image with defects drawn
    """
    result = image.copy()
    
    for defect in defects:
        if defect['class'] == 'crack':
            color = (0, 255, 0)  # Green
        elif defect['class'] == 'spalling':
            color = (0, 255, 255)  # Yellow
        else:
            color = (255, 0, 0)  # Red
        
        bbox = defect['bbox_xyxy']
        
        # Draw mask
        if show_masks and 'mask' in defect:
            mask = defect['mask']
            overlay = np.zeros_like(result)
            overlay[mask > 0] = color
            result = cv2.addWeighted(result, 0.7, overlay, 0.3, 0)
        
        # Draw box
        if show_boxes:
            cv2.rectangle(
                result,
                (bbox[0], bbox[1]),
                (bbox[2], bbox[3]),
                color,
                2
            )
        
        # Draw label
        if show_labels:
            label = f"{defect['class']}"
            cv2.putText(
                result,
                label,
                (bbox[0], bbox[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )
    
    return result


def depth_to_colormap(
    depth_map: np.ndarray,
    min_depth: Optional[float] = None,
    max_depth: Optional[float] = None,
    colormap: int = cv2.COLORMAP_JET,
) -> np.ndarray:
    """
    Convert depth map to color visualization.
    
    Args:
        depth_map: Depth in meters (H, W)
        min_depth: Minimum depth for color mapping (auto if None)
        max_depth: Maximum depth for color mapping (auto if None)
        colormap: OpenCV colormap
        
    Returns:
        depth_color: RGB visualization (H, W, 3)
    """
    # Handle invalid depths
    valid_mask = np.isfinite(depth_map) & (depth_map > 0)
    
    if not np.any(valid_mask):
        # Return black image if no valid depths
        return np.zeros((*depth_map.shape, 3), dtype=np.uint8)
    
    # Auto range
    if min_depth is None:
        min_depth = np.min(depth_map[valid_mask])
    if max_depth is None:
        max_depth = np.max(depth_map[valid_mask])
    
    # Normalize to 0-255
    depth_normalized = np.clip(
        (depth_map - min_depth) / (max_depth - min_depth) * 255,
        0,
        255
    ).astype(np.uint8)
    
    # Apply colormap
    depth_color = cv2.applyColorMap(depth_normalized, colormap)
    depth_color = cv2.cvtColor(depth_color, cv2.COLOR_BGR2RGB)
    
    # Mask invalid regions as black
    depth_color[~valid_mask] = 0
    
    return depth_color
