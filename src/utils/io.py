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


def get_frame_paths(output_dir: str, frame_id: int) -> Dict[str, str]:
    """
    Get standard file paths for a frame.
    
    Args:
        output_dir: Base output directory
        frame_id: Frame number
        
    Returns:
        paths: Dictionary of file paths
    """
    output_dir = Path(output_dir)
    frame_str = format_frame_id(frame_id)
    
    paths = {
        'rgb': str(output_dir / f"frame_{frame_str}_rgb.png"),
        'depth_vis': str(output_dir / f"frame_{frame_str}_depth.png"),
        'depth_npy': str(output_dir / f"frame_{frame_str}_depth.npy"),
        'metadata': str(output_dir / f"frame_{frame_str}_metadata.json"),
        'detection': str(output_dir / f"frame_{frame_str}_detection.json"),
        'geometry': str(output_dir / f"frame_{frame_str}_geometry.json"),
        'metrology': str(output_dir / f"frame_{frame_str}_metrology.json"),
        'verification': str(output_dir / f"frame_{frame_str}_verification.json"),
        'masks_dir': str(output_dir / "annotations" / "masks"),
    }
    
    return paths
