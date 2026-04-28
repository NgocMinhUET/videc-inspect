"""
Annotation JSON writers for ViDEC-Inspect.

Implements 4-layer annotation schema:
1. Detection: bbox, mask, class
2. Geometry: skeleton, contour, topology
3. Metrology: physical measurements
4. Verification: evidence requirements
"""

import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import cv2


def write_detection_json(
    frame_id: int,
    episode_id: str,
    image_size: tuple,
    cracks: List[Dict],
    spalls: List[Dict],
    negatives: List[Dict],
    masks_dir: str,
) -> Dict:
    """
    Write detection layer JSON.
    
    Args:
        frame_id: Frame number
        episode_id: Episode identifier
        image_size: (width, height)
        cracks: List of crack defects
        spalls: List of spalling defects
        negatives: List of hard negatives
        masks_dir: Directory to save mask images
        
    Returns:
        detection_dict: Detection annotation dictionary
    """
    width, height = image_size
    
    Path(masks_dir).mkdir(parents=True, exist_ok=True)
    
    defects_list = []
    
    # Process cracks
    for crack in cracks:
        # Save mask
        mask_filename = f"frame_{frame_id:06d}_{crack['defect_id']}.png"
        mask_path = Path(masks_dir) / mask_filename
        cv2.imwrite(str(mask_path), crack['mask'])
        
        defect_entry = {
            "defect_id": crack['defect_id'],
            "class": "crack",
            "bbox_xyxy": crack['bbox_xyxy'],
            "bbox_xywh": _xyxy_to_xywh(crack['bbox_xyxy']),
            "mask_path": f"annotations/masks/{mask_filename}",
            "mask_area_pixels": crack['mask_area_pixels'],
            "confidence": 1.0,
        }
        defects_list.append(defect_entry)
    
    # Process spalls
    for spall in spalls:
        # Save mask
        mask_filename = f"frame_{frame_id:06d}_{spall['defect_id']}.png"
        mask_path = Path(masks_dir) / mask_filename
        cv2.imwrite(str(mask_path), spall['mask'])
        
        defect_entry = {
            "defect_id": spall['defect_id'],
            "class": "spalling",
            "bbox_xyxy": spall['bbox_xyxy'],
            "bbox_xywh": _xyxy_to_xywh(spall['bbox_xyxy']),
            "mask_path": f"annotations/masks/{mask_filename}",
            "mask_area_pixels": spall['mask_area_pixels'],
            "confidence": 1.0,
        }
        defects_list.append(defect_entry)
    
    # Process hard negatives
    negatives_list = []
    for negative in negatives:
        negative_entry = {
            "negative_id": negative['negative_id'],
            "type": negative['type'],
            "bbox_xyxy": negative['bbox_xyxy'],
            "reason": negative['distinguishing_feature'],
        }
        negatives_list.append(negative_entry)
    
    detection_dict = {
        "frame_id": frame_id,
        "episode_id": episode_id,
        "image_width": width,
        "image_height": height,
        "num_defects": len(defects_list),
        "defects": defects_list,
        "hard_negatives": negatives_list,
    }
    
    return detection_dict


def write_geometry_json(
    frame_id: int,
    cracks: List[Dict],
    spalls: List[Dict],
) -> Dict:
    """
    Write geometry layer JSON.
    
    Args:
        frame_id: Frame number
        cracks: List of crack defects
        spalls: List of spalling defects
        
    Returns:
        geometry_dict: Geometry annotation dictionary
    """
    defects_geometry = []
    
    # Process cracks
    for crack in cracks:
        skeleton_coords = crack.get('skeleton_px', [])
        
        geometry_entry = {
            "defect_id": crack['defect_id'],
            "class": "crack",
            "skeleton": {
                "type": "polyline",
                "coordinates_px": skeleton_coords,
                "length_px": float(crack.get('length_px', 0)),
                "num_segments": len(skeleton_coords) - 1 if skeleton_coords else 0,
            },
            "branch_points": [],  # Not implemented yet
            "contour": None,  # Cracks typically don't have contours
        }
        defects_geometry.append(geometry_entry)
    
    # Process spalls
    for spall in spalls:
        contour_coords = spall.get('contour_px', [])
        
        geometry_entry = {
            "defect_id": spall['defect_id'],
            "class": "spalling",
            "contour": {
                "type": "polygon",
                "coordinates_px": contour_coords,
                "area_px": spall.get('mask_area_pixels', 0),
                "perimeter_px": float(spall.get('perimeter_px', 0)),
            },
            "major_axis_deg": float(spall.get('major_axis_deg', 0)),
            "minor_axis_ratio": float(spall.get('minor_axis_ratio', 1.0)),
        }
        defects_geometry.append(geometry_entry)
    
    geometry_dict = {
        "frame_id": frame_id,
        "defects_geometry": defects_geometry,
    }
    
    return geometry_dict


def write_metrology_json(
    frame_id: int,
    cracks: List[Dict],
    spalls: List[Dict],
    pixel_to_meter: float,
    mean_distance_to_wall: float,
    camera_params: Optional[Dict] = None,
) -> Dict:
    """
    Write metrology layer JSON.
    
    Args:
        frame_id: Frame number
        cracks: List of crack defects
        spalls: List of spalling defects
        pixel_to_meter: Conversion factor
        mean_distance_to_wall: Distance to wall in meters
        camera_params: Camera parameters dictionary
        
    Returns:
        metrology_dict: Metrology annotation dictionary
    """
    if camera_params is None:
        camera_params = {
            "focal_length_px": 1100.0,
            "baseline_m": 0.12,
            "principal_point": [960, 540],
        }
    
    defects_metrology = []
    
    # Process cracks
    for crack in cracks:
        # Width profile
        width_profile_mm = crack.get('width_profile_mm', [])
        
        if len(width_profile_mm) > 0:
            num_measurements = len(width_profile_mm)
            positions_normalized = np.linspace(0, 1, num_measurements).tolist()
        else:
            num_measurements = 0
            positions_normalized = []
        
        metrology_entry = {
            "defect_id": crack['defect_id'],
            "class": "crack",
            "length_m": float(crack.get('length_m', 0)),
            "width_profile": {
                "num_measurements": num_measurements,
                "positions_normalized": positions_normalized,
                "widths_mm": [float(w) for w in width_profile_mm],
                "mean_width_mm": float(crack.get('mean_width_mm', 0)),
                "max_width_mm": float(crack.get('max_width_mm', 0)),
                "width_std_mm": float(crack.get('width_std_mm', 0)),
            },
            "severity": crack['severity'],
            "severity_criteria": {
                "method": "width_based",
                "threshold_minor_mm": 1.0,
                "threshold_moderate_mm": 2.0,
                "threshold_severe_mm": 4.0,
            },
        }
        defects_metrology.append(metrology_entry)
    
    # Process spalls
    for spall in spalls:
        metrology_entry = {
            "defect_id": spall['defect_id'],
            "class": "spalling",
            "area_m2": float(spall.get('area_m2', 0)),
            "depth_mm": float(spall.get('depth_mm', 0)),
            "volume_cm3": float(spall.get('volume_cm3', 0)),
            "severity": spall['severity'],
            "severity_criteria": {
                "method": "depth_based",
                "threshold_minor_mm": 5.0,
                "threshold_moderate_mm": 10.0,
                "threshold_severe_mm": 20.0,
            },
        }
        defects_metrology.append(metrology_entry)
    
    metrology_dict = {
        "frame_id": frame_id,
        "camera_parameters": camera_params,
        "mean_distance_to_wall_m": float(mean_distance_to_wall),
        "pixel_to_meter_ratio": float(pixel_to_meter),
        "defects_metrology": defects_metrology,
    }
    
    return metrology_dict


def write_verification_json(
    frame_id: int,
    cracks: List[Dict],
    spalls: List[Dict],
    negatives: List[Dict],
    image_quality: Optional[Dict] = None,
) -> Dict:
    """
    Write verification layer JSON.
    
    Args:
        frame_id: Frame number
        cracks: List of crack defects
        spalls: List of spalling defects
        negatives: List of hard negatives
        image_quality: Image quality metrics
        
    Returns:
        verification_dict: Verification annotation dictionary
    """
    if image_quality is None:
        image_quality = {
            "sharpness_score": 0.75,
            "contrast_score": 0.70,
            "snr_db": 20.0,
        }
    
    defects_verification = []
    
    # Process cracks
    for crack in cracks:
        verification_entry = {
            "defect_id": crack['defect_id'],
            "class": "crack",
            "visibility": "partial" if crack['difficulty'] == "hard" else "clear",
            "occlusion_ratio": 0.15 if crack['difficulty'] == "hard" else 0.0,
            "image_quality": image_quality.copy(),
            "minimal_evidence_level": crack.get('minimal_evidence_level', 'roi_plus_skeleton'),
            "evidence_available": {
                "has_roi": True,
                "has_mask": True,
                "has_skeleton": True,
                "has_width_profile": True,
            },
            "verification_status": "confirmed",
            "requires_closeup": crack.get('requires_closeup', True),
            "closeup_benefit": {
                "expected_improvement": "width_measurement_refinement",
                "priority": "medium" if crack['severity'] in ["moderate", "severe"] else "low",
            },
            "ambiguity_zone": crack['difficulty'] == "hard",
            "ambiguity_reason": "low_contrast" if crack['difficulty'] == "hard" else None,
            "confusable_with": [],
            "ground_truth_confidence": 1.0,
        }
        defects_verification.append(verification_entry)
    
    # Process spalls
    for spall in spalls:
        verification_entry = {
            "defect_id": spall['defect_id'],
            "class": "spalling",
            "visibility": "partial" if spall['difficulty'] == "hard" else "clear",
            "occlusion_ratio": 0.10 if spall['difficulty'] == "hard" else 0.0,
            "image_quality": image_quality.copy(),
            "minimal_evidence_level": spall.get('minimal_evidence_level', 'roi_plus_area'),
            "evidence_available": {
                "has_roi": True,
                "has_mask": True,
                "has_depth": True,
                "has_volume": True,
            },
            "verification_status": "confirmed",
            "requires_closeup": spall.get('requires_closeup', False),
            "closeup_benefit": {
                "expected_improvement": "depth_measurement_refinement",
                "priority": "low" if spall['difficulty'] == "easy" else "medium",
            },
            "ambiguity_zone": spall['difficulty'] == "hard",
            "ambiguity_reason": "low_contrast" if spall['difficulty'] == "hard" else None,
            "confusable_with": [],
            "ground_truth_confidence": 1.0,
        }
        defects_verification.append(verification_entry)
    
    # Process hard negatives
    negatives_verification = []
    for negative in negatives:
        verification_entry = {
            "negative_id": negative['negative_id'],
            "type": negative['type'],
            "designed_to_confuse": negative.get('confusable_with', 'unknown'),
            "distinguishing_feature": negative.get('distinguishing_feature', 'unknown'),
            "verification_difficulty": negative['difficulty'],
        }
        negatives_verification.append(verification_entry)
    
    verification_dict = {
        "frame_id": frame_id,
        "defects_verification": defects_verification,
        "hard_negatives_verification": negatives_verification,
    }
    
    return verification_dict


def write_metadata_json(
    frame_id: int,
    episode_id: str,
    timestamp_sec: float,
    robot_state: Dict,
    camera_state: Dict,
    environment: Dict,
    defect_ids: List[str],
    negative_ids: List[str],
) -> Dict:
    """
    Write frame metadata JSON.
    
    Args:
        frame_id: Frame number
        episode_id: Episode identifier
        timestamp_sec: Time since episode start
        robot_state: Robot position, orientation, velocity
        camera_state: Camera pose relative to wall
        environment: Environmental conditions
        defect_ids: List of defect IDs in view
        negative_ids: List of negative IDs in view
        
    Returns:
        metadata_dict: Metadata dictionary
    """
    metadata_dict = {
        "frame_id": frame_id,
        "episode_id": episode_id,
        "timestamp_sec": float(timestamp_sec),
        "robot_state": robot_state,
        "camera_state": camera_state,
        "environment": environment,
        "defect_ids_in_view": defect_ids,
        "negative_ids_in_view": negative_ids,
    }
    
    return metadata_dict


def _xyxy_to_xywh(bbox_xyxy: List[int]) -> List[int]:
    """Convert bbox from [x_min, y_min, x_max, y_max] to [x, y, w, h]."""
    x_min, y_min, x_max, y_max = bbox_xyxy
    return [x_min, y_min, x_max - x_min, y_max - y_min]
