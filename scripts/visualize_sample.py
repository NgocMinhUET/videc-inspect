"""
Visualization script for ViDEC-Inspect dataset samples.

Visualizes generated frames with annotations overlaid.

Usage:
    python scripts/visualize_sample.py --data_dir data/raw/v01 --frame_id 0
"""

import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import cv2
import matplotlib.pyplot as plt

from src.utils.io import load_json, get_frame_paths
from src.utils.vis import visualize_frame, depth_to_colormap


def visualize_sample(data_dir: str, frame_id: int, save_output: bool = False):
    """
    Visualize a single frame with annotations.
    
    Args:
        data_dir: Dataset directory
        frame_id: Frame ID to visualize
        save_output: Whether to save visualization
    """
    print(f"Visualizing frame {frame_id} from {data_dir}")
    
    # Get file paths
    paths = get_frame_paths(data_dir, frame_id)
    
    # Load RGB image
    rgb_path = Path(paths['rgb'])
    if not rgb_path.exists():
        print(f"Error: RGB image not found: {rgb_path}")
        return
    
    rgb_image = cv2.imread(str(rgb_path))
    rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)
    
    # Load depth map
    depth_map = None
    depth_npy_path = Path(paths['depth_npy'])
    if depth_npy_path.exists():
        depth_map = np.load(str(depth_npy_path))
    
    # Load annotations
    detection_path = Path(paths['detection'])
    if not detection_path.exists():
        print(f"Error: Detection annotations not found: {detection_path}")
        return
    
    detection_json = load_json(str(detection_path))
    geometry_json = load_json(str(paths['geometry']))
    metrology_json = load_json(str(paths['metrology']))
    verification_json = load_json(str(paths['verification']))
    metadata_json = load_json(str(paths['metadata']))
    
    # Reconstruct defect dictionaries for visualization
    defects = []
    negatives = []
    
    for defect_entry in detection_json['defects']:
        # Load mask
        mask_path = Path(data_dir) / defect_entry['mask_path']
        if mask_path.exists():
            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        else:
            mask = None
        
        # Find corresponding geometry and metrology
        defect_id = defect_entry['defect_id']
        
        # Find geometry
        skeleton_px = None
        for geom in geometry_json['defects_geometry']:
            if geom['defect_id'] == defect_id:
                if 'skeleton' in geom and geom['skeleton']:
                    skeleton_px = geom['skeleton']['coordinates_px']
                break
        
        # Find metrology
        severity = "unknown"
        for metro in metrology_json['defects_metrology']:
            if metro['defect_id'] == defect_id:
                severity = metro['severity']
                break
        
        defect = {
            'defect_id': defect_id,
            'class': defect_entry['class'],
            'bbox_xyxy': defect_entry['bbox_xyxy'],
            'mask': mask,
            'skeleton_px': skeleton_px,
            'severity': severity,
            'difficulty': 'medium',  # Not stored in detection JSON
        }
        defects.append(defect)
    
    for negative_entry in detection_json['hard_negatives']:
        negatives.append({
            'negative_id': negative_entry['negative_id'],
            'type': negative_entry['type'],
            'bbox_xyxy': negative_entry['bbox_xyxy'],
        })
    
    # Create visualization
    vis_image = visualize_frame(
        rgb_image=rgb_image,
        depth_map=depth_map,
        defects=defects,
        negatives=negatives,
        show_masks=True,
        show_skeletons=True,
    )
    
    # Display using matplotlib
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # Original image
    axes[0].imshow(rgb_image)
    axes[0].set_title("Original RGB")
    axes[0].axis('off')
    
    # Depth map
    if depth_map is not None:
        depth_vis = depth_to_colormap(depth_map)
        axes[1].imshow(depth_vis)
        axes[1].set_title("Depth Map")
    else:
        axes[1].text(0.5, 0.5, "No depth map", ha='center', va='center')
        axes[1].set_title("Depth Map")
    axes[1].axis('off')
    
    # Annotated image
    axes[2].imshow(vis_image)
    axes[2].set_title("Annotated")
    axes[2].axis('off')
    
    plt.suptitle(f"Frame {frame_id} - Episode: {metadata_json['episode_id']}", fontsize=14)
    plt.tight_layout()
    
    # Save if requested
    if save_output:
        output_path = Path(data_dir) / "preview" / f"frame_{frame_id:06d}_preview.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved visualization to: {output_path}")
    
    plt.show()
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Frame {frame_id} Summary")
    print("=" * 60)
    print(f"Episode ID: {metadata_json['episode_id']}")
    print(f"Timestamp: {metadata_json['timestamp_sec']:.2f}s")
    print(f"Number of defects: {len(defects)}")
    for defect in defects:
        print(f"  - {defect['class']}: {defect['defect_id']} ({defect['severity']})")
    print(f"Number of hard negatives: {len(negatives)}")
    for negative in negatives:
        print(f"  - {negative['type']}: {negative['negative_id']}")
    print(f"Environment: {metadata_json['environment']['water_clarity']}, " +
          f"{metadata_json['environment']['lighting']} lighting")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Visualize ViDEC-Inspect dataset samples"
    )
    
    parser.add_argument(
        '--data_dir',
        type=str,
        required=True,
        help='Dataset directory path'
    )
    
    parser.add_argument(
        '--frame_id',
        type=int,
        default=0,
        help='Frame ID to visualize (default: 0)'
    )
    
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save visualization to file'
    )
    
    args = parser.parse_args()
    
    visualize_sample(
        data_dir=args.data_dir,
        frame_id=args.frame_id,
        save_output=args.save,
    )


if __name__ == "__main__":
    main()
