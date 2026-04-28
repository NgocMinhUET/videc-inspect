"""Utility modules for ViDEC-Inspect."""

from .io import save_json, load_json, ensure_dir, get_frame_paths
from .vis import visualize_frame, draw_defects_on_image, depth_to_colormap
from .config import benchmark_config
from .depth_modifier import apply_spall_to_depth_map, apply_crack_to_depth_map, compute_depth_quality_metrics

__all__ = [
    'save_json',
    'load_json',
    'ensure_dir',
    'get_frame_paths',
    'visualize_frame',
    'draw_defects_on_image',
    'depth_to_colormap',
    'benchmark_config',
    'apply_spall_to_depth_map',
    'apply_crack_to_depth_map',
    'compute_depth_quality_metrics',
]
