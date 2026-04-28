"""I/O utilities for ViDEC-Inspect."""

import json
import numpy as np
from pathlib import Path
from typing import Any, Dict


def save_json(data: Dict, filepath: str, indent: int = 2):
    """
    Save dictionary to JSON file.
    
    Args:
        data: Dictionary to save
        filepath: Output file path
        indent: JSON indentation level
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=indent, cls=NumpyEncoder)


def load_json(filepath: str) -> Dict:
    """
    Load JSON file.
    
    Args:
        filepath: JSON file path
        
    Returns:
        data: Loaded dictionary
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data


def ensure_dir(dirpath: str):
    """
    Ensure directory exists, create if not.
    
    Args:
        dirpath: Directory path
    """
    Path(dirpath).mkdir(parents=True, exist_ok=True)


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""
    
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def format_frame_id(frame_id: int, width: int = 6) -> str:
    """
    Format frame ID with zero-padding.
    
    Args:
        frame_id: Frame number
        width: Total width of formatted string
        
    Returns:
        formatted: Zero-padded string
    """
    return str(frame_id).zfill(width)


def get_frame_paths(output_dir: str, episode_id: int, frame_id: int) -> Dict[str, str]:
    """
    Get standard file paths for a frame with proper episode/frame structure.
    
    New structure:
        episode_00000/
            frame_000000/
                rgb.png
                depth.png
                depth.npy
                metadata.json
                annotations/
                    detection.json
                    geometry.json
                    metrology.json
                    verification.json
                    masks/
                        crack_0000.png
    
    Args:
        output_dir: Base output directory
        episode_id: Episode number
        frame_id: Frame number
        
    Returns:
        paths: Dictionary of file paths
    """
    output_dir = Path(output_dir)
    episode_str = f"episode_{episode_id:05d}"
    frame_str = f"frame_{frame_id:06d}"
    
    episode_dir = output_dir / episode_str
    frame_dir = episode_dir / frame_str
    annotations_dir = frame_dir / "annotations"
    masks_dir = annotations_dir / "masks"
    
    paths = {
        'episode_dir': str(episode_dir),
        'frame_dir': str(frame_dir),
        'rgb': str(frame_dir / "rgb.png"),
        'depth_vis': str(frame_dir / "depth.png"),
        'depth_npy': str(frame_dir / "depth.npy"),
        'metadata': str(frame_dir / "metadata.json"),
        'detection': str(annotations_dir / "detection.json"),
        'geometry': str(annotations_dir / "geometry.json"),
        'metrology': str(annotations_dir / "metrology.json"),
        'verification': str(annotations_dir / "verification.json"),
        'masks_dir': str(masks_dir),
    }
    
    return paths
