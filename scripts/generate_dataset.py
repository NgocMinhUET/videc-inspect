"""
Main dataset generation script for ViDEC-Inspect v0.1.

Generates benchmark dataset with:
- HoloOcean flat wall inspection episodes
- Synthetic crack, spalling, and hard negative defects
- 4-layer annotations (detection, geometry, metrology, verification)
- RGB + Depth + metadata

Usage:
    python scripts/generate_dataset.py --num_episodes 100 --output data/raw/v01
"""

import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import cv2
from tqdm import tqdm

# Local imports
from src.defects.injector import DefectInjector
from src.annotations.writers import (
    write_detection_json,
    write_geometry_json,
    write_metrology_json,
    write_verification_json,
    write_metadata_json,
)
from src.utils.io import save_json, ensure_dir, get_frame_paths
from src.utils.vis import depth_to_colormap


def generate_synthetic_frame(
    frame_size=(1920, 1080),
    standoff_distance_m=1.5,
):
    """
    Generate synthetic flat wall frame (placeholder until HoloOcean integration).
    
    Args:
        frame_size: (width, height) in pixels
        standoff_distance_m: Distance to wall in meters
        
    Returns:
        rgb_image: Synthetic RGB image
        depth_map: Synthetic depth map
        pixel_to_meter: Conversion factor
    """
    width, height = frame_size
    
    # Generate concrete texture
    rgb_image = np.random.randint(100, 140, (height, width, 3), dtype=np.uint8)
    
    # Add some texture variation
    noise = np.random.randn(height, width, 3) * 10
    rgb_image = np.clip(rgb_image + noise, 0, 255).astype(np.uint8)
    
    # Generate depth map (flat wall at standoff distance)
    depth_map = np.full((height, width), standoff_distance_m, dtype=np.float32)
    
    # Add slight depth noise
    depth_noise = np.random.randn(height, width) * 0.005
    depth_map += depth_noise
    
    # Calculate pixel to meter ratio (simplified)
    # Assuming camera FOV ~90 degrees
    fov_rad = np.deg2rad(90)
    frame_width_m = 2 * standoff_distance_m * np.tan(fov_rad / 2)
    pixel_to_meter = frame_width_m / width
    
    return rgb_image, depth_map, pixel_to_meter


def generate_episode(
    episode_id: int,
    output_dir: str,
    num_frames: int = 10,
    defect_params: dict = None,
):
    """
    Generate a single inspection episode.
    
    Args:
        episode_id: Episode number
        output_dir: Output directory path
        num_frames: Number of frames per episode
        defect_params: Defect generation parameters
    """
    if defect_params is None:
        defect_params = {
            'num_cracks': 1,
            'num_spalls': 1,
            'num_negatives': 1,
        }
    
    episode_str = f"flatwall_{episode_id:05d}"
    print(f"\n[Episode {episode_id}] Generating '{episode_str}' with {num_frames} frames...")
    
    # Initialize defect injector
    injector = DefectInjector()
    
    # Generate defect scene (same defects across episode)
    frame_size = (1920, 1080)
    standoff_distance = 1.5  # meters
    
    # Generate synthetic frame
    base_rgb, depth_map, pixel_to_meter = generate_synthetic_frame(
        frame_size=frame_size,
        standoff_distance_m=standoff_distance
    )
    
    # Generate defect scene
    scene = injector.generate_scene(
        image_size=frame_size,
        pixel_to_meter=pixel_to_meter,
        num_cracks=defect_params['num_cracks'],
        num_spalls=defect_params['num_spalls'],
        num_negatives=defect_params['num_negatives'],
    )
    
    # Composite defects onto base image
    rgb_with_defects = injector.composite_defects_on_image(
        base_image=base_rgb,
        scene=scene
    )
    
    # Generate frames
    for frame_idx in range(num_frames):
        frame_id = episode_id * 1000 + frame_idx
        
        # Get output paths
        paths = get_frame_paths(output_dir, frame_id)
        
        # Save RGB image
        ensure_dir(Path(paths['rgb']).parent)
        cv2.imwrite(paths['rgb'], cv2.cvtColor(rgb_with_defects, cv2.COLOR_RGB2BGR))
        
        # Save depth visualization
        depth_vis = depth_to_colormap(depth_map)
        cv2.imwrite(paths['depth_vis'], cv2.cvtColor(depth_vis, cv2.COLOR_RGB2BGR))
        
        # Save depth numpy array
        np.save(paths['depth_npy'], depth_map)
        
        # Write 4-layer annotations
        
        # Layer 1: Detection
        detection_json = write_detection_json(
            frame_id=frame_id,
            episode_id=episode_str,
            image_size=frame_size,
            cracks=scene['cracks'],
            spalls=scene['spalls'],
            negatives=scene['negatives'],
            masks_dir=paths['masks_dir'],
        )
        save_json(detection_json, paths['detection'])
        
        # Layer 2: Geometry
        geometry_json = write_geometry_json(
            frame_id=frame_id,
            cracks=scene['cracks'],
            spalls=scene['spalls'],
        )
        save_json(geometry_json, paths['geometry'])
        
        # Layer 3: Metrology
        metrology_json = write_metrology_json(
            frame_id=frame_id,
            cracks=scene['cracks'],
            spalls=scene['spalls'],
            pixel_to_meter=pixel_to_meter,
            mean_distance_to_wall=standoff_distance,
        )
        save_json(metrology_json, paths['metrology'])
        
        # Layer 4: Verification
        verification_json = write_verification_json(
            frame_id=frame_id,
            cracks=scene['cracks'],
            spalls=scene['spalls'],
            negatives=scene['negatives'],
        )
        save_json(verification_json, paths['verification'])
        
        # Metadata
        defect_ids = [c['defect_id'] for c in scene['cracks']] + \
                     [s['defect_id'] for s in scene['spalls']]
        negative_ids = [n['negative_id'] for n in scene['negatives']]
        
        metadata_json = write_metadata_json(
            frame_id=frame_id,
            episode_id=episode_str,
            timestamp_sec=frame_idx * 0.2,  # 5Hz
            robot_state={
                "position_m": [2.0 + frame_idx * 0.1, -standoff_distance, -5.0],
                "orientation_deg": [0.0, 0.0, 180.0],
                "velocity_m_s": [0.1, 0.0, 0.0],
            },
            camera_state={
                "distance_to_wall_m": standoff_distance,
                "view_angle_deg": 0.0,
                "look_at_point": [2.0 + frame_idx * 0.1, 0.0, -5.0],
            },
            environment={
                "water_clarity": "moderate",
                "visibility_m": 8.5,
                "lighting": "normal",
                "ambient_illumination_lux": 300,
                "artificial_light": True,
            },
            defect_ids=defect_ids,
            negative_ids=negative_ids,
        )
        save_json(metadata_json, paths['metadata'])
    
    print(f"[Episode {episode_id}] ✓ Generated {num_frames} frames")
    print(f"  - Cracks: {len(scene['cracks'])}")
    print(f"  - Spalls: {len(scene['spalls'])}")
    print(f"  - Hard negatives: {len(scene['negatives'])}")


def generate_dataset(
    num_episodes: int,
    output_dir: str,
    frames_per_episode: int = 10,
    defect_config: dict = None,
):
    """
    Generate complete ViDEC-Inspect dataset.
    
    Args:
        num_episodes: Number of episodes to generate
        output_dir: Output directory path
        frames_per_episode: Frames per episode
        defect_config: Defect generation configuration
    """
    print("=" * 70)
    print("ViDEC-Inspect v0.1 Dataset Generation")
    print("=" * 70)
    print(f"Output directory: {output_dir}")
    print(f"Episodes: {num_episodes}")
    print(f"Frames per episode: {frames_per_episode}")
    print(f"Total frames: {num_episodes * frames_per_episode}")
    print("=" * 70)
    
    # Create output directory
    ensure_dir(output_dir)
    
    # Default defect config
    if defect_config is None:
        defect_config = {
            'num_cracks': 1,
            'num_spalls': 1,
            'num_negatives': 1,
        }
    
    # Generate episodes
    for episode_id in tqdm(range(num_episodes), desc="Generating episodes"):
        generate_episode(
            episode_id=episode_id,
            output_dir=output_dir,
            num_frames=frames_per_episode,
            defect_params=defect_config,
        )
    
    # Generate dataset summary
    total_frames = num_episodes * frames_per_episode
    summary = {
        "dataset_version": "v0.1",
        "num_episodes": num_episodes,
        "frames_per_episode": frames_per_episode,
        "total_frames": total_frames,
        "defect_config": defect_config,
        "annotation_layers": ["detection", "geometry", "metrology", "verification"],
        "sensors": ["RGB", "Depth"],
    }
    
    summary_path = Path(output_dir) / "dataset_summary.json"
    save_json(summary, str(summary_path))
    
    print("\n" + "=" * 70)
    print("✓ Dataset generation complete!")
    print(f"✓ Generated {total_frames} frames in {num_episodes} episodes")
    print(f"✓ Output: {output_dir}")
    print(f"✓ Summary: {summary_path}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Generate ViDEC-Inspect v0.1 benchmark dataset"
    )
    
    parser.add_argument(
        '--num_episodes',
        type=int,
        default=10,
        help='Number of episodes to generate (default: 10)'
    )
    
    parser.add_argument(
        '--frames_per_episode',
        type=int,
        default=10,
        help='Number of frames per episode (default: 10)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='data/raw/v01',
        help='Output directory (default: data/raw/v01)'
    )
    
    parser.add_argument(
        '--num_cracks',
        type=int,
        default=1,
        help='Number of cracks per scene (default: 1)'
    )
    
    parser.add_argument(
        '--num_spalls',
        type=int,
        default=1,
        help='Number of spalls per scene (default: 1)'
    )
    
    parser.add_argument(
        '--num_negatives',
        type=int,
        default=1,
        help='Number of hard negatives per scene (default: 1)'
    )
    
    args = parser.parse_args()
    
    # Prepare defect config
    defect_config = {
        'num_cracks': args.num_cracks,
        'num_spalls': args.num_spalls,
        'num_negatives': args.num_negatives,
    }
    
    # Generate dataset
    generate_dataset(
        num_episodes=args.num_episodes,
        output_dir=args.output,
        frames_per_episode=args.frames_per_episode,
        defect_config=defect_config,
    )


if __name__ == "__main__":
    main()
