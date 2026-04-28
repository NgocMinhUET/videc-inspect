"""
Dataset generation script for ViDEC-Inspect v0.1 (REVISED P1)

IMPORTANT CHANGES FROM v1:
1. Renamed generate_synthetic_frame() → generate_placeholder_flat_wall_frame()
   - Makes it clear this is NOT real HoloOcean data yet
   - Real HoloOcean integration is TODO
   
2. Episode dynamics: frames now vary by viewpoint/distance
   - Robot moves along trajectory
   - Different observations per frame
   
3. Depth consistency: spall defects modify depth maps
   - Uses apply_spall_to_depth_map()
   - Depth now consistent with metrology
   
4. Standardized schema:
   - class → class_name
   - "spalling" → "spall"
   - Added benchmark metadata
   - scene_id tracking
   
5. Dataset protocol:
   - Saves random seed
   - Saves config snapshot
   - Creates train/val/test splits
   - Episode/frame structure

Usage:
    python scripts/generate_dataset_v2.py --num_episodes 100 --output data/raw/v01 --seed 42
"""

import argparse
import sys
import json
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
from src.utils import (
    save_json, ensure_dir, get_frame_paths,
    apply_spall_to_depth_map, apply_crack_to_depth_map,
    compute_depth_quality_metrics, depth_to_colormap,
    benchmark_config,
)


def generate_placeholder_flat_wall_frame(
    frame_size=(1920, 1080),
    standoff_distance_m=1.5,
    view_angle_deg=0.0,
    seed=None,
):
    """
    Generate PLACEHOLDER flat wall frame (NOT HoloOcean yet).
    
    TODO Phase 1 Week 3: Replace with real HoloOcean capture:
        env = holoocean.make(scenario_cfg=scenario)
        env.set_state({...pose...})
        state = env.tick()
        rgb = state['FrontCamera']
        depth = state['FrontDepth']['depth']
    
    Args:
        frame_size: (width, height) in pixels
        standoff_distance_m: Distance to wall in meters
        view_angle_deg: View angle relative to wall normal
        seed: Random seed for reproducibility
        
    Returns:
        rgb_image: Placeholder RGB image
        depth_map: Placeholder depth map
        pixel_to_meter: Conversion factor
    """
    if seed is not None:
        np.random.seed(seed)
    
    width, height = frame_size
    
    # Generate concrete texture (placeholder)
    base_color = np.random.randint(100, 140)
    rgb_image = np.full((height, width, 3), base_color, dtype=np.uint8)
    
    # Add realistic texture variation
    noise = np.random.randn(height, width, 3) * 15
    rgb_image = np.clip(rgb_image + noise, 0, 255).astype(np.uint8)
    
    # Add subtle patterns
    for _ in range(3):
        cx = np.random.randint(0, width)
        cy = np.random.randint(0, height)
        radius = np.random.randint(50, 200)
        cv2.circle(rgb_image, (cx, cy), radius, 
                   tuple(np.random.randint(90, 150, 3).tolist()), -1)
    
    rgb_image = cv2.GaussianBlur(rgb_image, (5, 5), 0)
    
    # Generate depth map (flat wall)
    depth_map = np.full((height, width), standoff_distance_m, dtype=np.float32)
    
    # Add depth noise (sensor noise)
    depth_noise = np.random.randn(height, width) * 0.005
    depth_map += depth_noise
    
    # Simulate view angle effect on depth
    if abs(view_angle_deg) > 5:
        # Oblique view: depth varies across image
        angle_rad = np.deg2rad(view_angle_deg)
        x_coords = np.linspace(-1, 1, width)
        depth_variation = x_coords * standoff_distance_m * np.tan(angle_rad) * 0.5
        depth_map += depth_variation[np.newaxis, :]
    
    # Calculate pixel to meter ratio
    fov_rad = np.deg2rad(benchmark_config.get_camera_params()['fov_deg'])
    frame_width_m = 2 * standoff_distance_m * np.tan(fov_rad / 2)
    pixel_to_meter = frame_width_m / width
    
    return rgb_image, depth_map, pixel_to_meter


def generate_episode(
    episode_id: int,
    output_dir: str,
    num_frames: int = 10,
    defect_params: dict = None,
    condition_params: dict = None,
    seed=None,
):
    """
    Generate single inspection episode with proper frame dynamics.
    
    IMPROVEMENTS FROM V1:
    - Frames vary by robot pose/viewpoint
    - Depth maps modified by spall geometry
    - Proper episode/frame file structure
    - Scene tracking
    
    Args:
        episode_id: Episode number
        output_dir: Output directory path
        num_frames: Number of frames per episode
        defect_params: Defect generation parameters
        condition_params: Environmental conditions
        seed: Random seed
    """
    if defect_params is None:
        defect_params = {
            'num_cracks': 1,
            'num_spalls': 1,
            'num_negatives': 1,
        }
    
    if condition_params is None:
        condition_params = {
            'water_clarity': 'moderate',
            'lighting': 'normal',
            'standoff_distance_m': 1.5,
        }
    
    if seed is not None:
        np.random.seed(seed + episode_id)
    
    episode_str = f"flatwall_{episode_id:05d}"
    scene_id = f"flat_wall_{episode_id:03d}"
    
    print(f"\n[Episode {episode_id}] '{episode_str}' - {num_frames} frames")
    
    # Initialize defect injector
    injector = DefectInjector()
    
    frame_size = (1920, 1080)
    standoff_base = condition_params['standoff_distance_m']
    
    # Generate defect scene (consistent across episode)
    # But observation varies per frame
    base_rgb, base_depth, pixel_to_meter = generate_placeholder_flat_wall_frame(
        frame_size=frame_size,
        standoff_distance_m=standoff_base,
        view_angle_deg=0.0,
        seed=seed + episode_id * 1000,
    )
    
    # Generate defects once per episode
    scene = injector.generate_scene(
        image_size=frame_size,
        pixel_to_meter=pixel_to_meter,
        num_cracks=defect_params['num_cracks'],
        num_spalls=defect_params['num_spalls'],
        num_negatives=defect_params['num_negatives'],
    )
    
    print(f"  Defects: {len(scene['cracks'])} cracks, {len(scene['spalls'])} spalls, "
          f"{len(scene['negatives'])} negatives")
    
    # Generate frames with dynamics
    for frame_idx in range(num_frames):
        frame_id = episode_id * 1000 + frame_idx
        
        # Vary observation per frame
        # Simulate robot moving along survey trajectory
        t = frame_idx / max(1, num_frames - 1)  # 0 to 1
        
        # Vary standoff distance slightly
        standoff_current = standoff_base + np.sin(t * np.pi * 2) * 0.2
        
        # Vary view angle
        view_angle = np.sin(t * np.pi * 4) * 10.0  # ±10 degrees
        
        # Generate frame with current pose
        rgb_clean, depth_clean, pixel_to_meter_current = generate_placeholder_flat_wall_frame(
            frame_size=frame_size,
            standoff_distance_m=standoff_current,
            view_angle_deg=view_angle,
            seed=seed + episode_id * 1000 + frame_idx,
        )
        
        # Composite defects onto RGB
        rgb_with_defects = injector.composite_defects_on_image(
            base_image=rgb_clean,
            scene=scene,
        )
        
        # CRITICAL: Modify depth map for spall geometry
        depth_with_defects = apply_spall_to_depth_map(
            depth_map=depth_clean,
            spalls=scene['spalls'],
            pixel_to_meter=pixel_to_meter_current,
        )
        
        depth_with_defects = apply_crack_to_depth_map(
            depth_map=depth_with_defects,
            cracks=scene['cracks'],
            pixel_to_meter=pixel_to_meter_current,
        )
        
        # Get output paths (new structure)
        paths = get_frame_paths(output_dir, episode_id, frame_id)
        
        # Ensure directories exist
        ensure_dir(paths['frame_dir'])
        ensure_dir(paths['masks_dir'])
        
        # Save RGB
        cv2.imwrite(paths['rgb'], cv2.cvtColor(rgb_with_defects, cv2.COLOR_RGB2BGR))
        
        # Save depth
        depth_vis = depth_to_colormap(depth_with_defects)
        cv2.imwrite(paths['depth_vis'], cv2.cvtColor(depth_vis, cv2.COLOR_RGB2BGR))
        np.save(paths['depth_npy'], depth_with_defects)
        
        # Compute depth quality for verification
        depth_quality = compute_depth_quality_metrics(depth_with_defects, standoff_current)
        
        # Write 4-layer annotations
        
        # Layer 1: Detection
        detection_json = write_detection_json(
            frame_id=frame_id,
            episode_id=episode_str,
            scene_id=scene_id,
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
            episode_id=episode_str,
            scene_id=scene_id,
            cracks=scene['cracks'],
            spalls=scene['spalls'],
        )
        save_json(geometry_json, paths['geometry'])
        
        # Layer 3: Metrology
        metrology_json = write_metrology_json(
            frame_id=frame_id,
            episode_id=episode_str,
            scene_id=scene_id,
            cracks=scene['cracks'],
            spalls=scene['spalls'],
            pixel_to_meter=pixel_to_meter_current,
            mean_distance_to_wall=standoff_current,
        )
        save_json(metrology_json, paths['metrology'])
        
        # Layer 4: Verification
        image_quality = {
            **depth_quality,
            'sharpness_score': 0.75,
            'contrast_score': 0.70,
        }
        
        verification_json = write_verification_json(
            frame_id=frame_id,
            episode_id=episode_str,
            scene_id=scene_id,
            cracks=scene['cracks'],
            spalls=scene['spalls'],
            negatives=scene['negatives'],
            image_quality=image_quality,
        )
        save_json(verification_json, paths['verification'])
        
        # Metadata
        defect_ids = [c['defect_id'] for c in scene['cracks']] + \
                     [s['defect_id'] for s in scene['spalls']]
        negative_ids = [n['negative_id'] for n in scene['negatives']]
        
        # Robot state with dynamics
        x_pos = 2.0 + (t * 6.0) - 3.0  # -1 to +5 m
        
        metadata_json = write_metadata_json(
            frame_id=frame_id,
            episode_id=episode_str,
            scene_id=scene_id,
            timestamp_sec=frame_idx * 0.2,  # 5Hz
            robot_state={
                "position_m": [x_pos, -standoff_current, -5.0],
                "orientation_deg": [0.0, view_angle, 180.0],
                "velocity_m_s": [0.1, 0.0, 0.0],
            },
            camera_state={
                "distance_to_wall_m": standoff_current,
                "view_angle_deg": view_angle,
                "look_at_point": [x_pos, 0.0, -5.0],
            },
            environment={
                "water_clarity": condition_params['water_clarity'],
                "visibility_m": 8.5,
                "lighting": condition_params['lighting'],
                "ambient_illumination_lux": 300,
                "artificial_light": True,
            },
            defect_ids=defect_ids,
            negative_ids=negative_ids,
        )
        save_json(metadata_json, paths['metadata'])
    
    print(f"[Episode {episode_id}] ✓ Complete")


def generate_splits(num_episodes: int, seed: int, train_ratio=0.7, val_ratio=0.15):
    """
    Generate reproducible train/val/test splits.
    
    Args:
        num_episodes: Total number of episodes
        seed: Random seed for reproducibility
        train_ratio: Fraction for training
        val_ratio: Fraction for validation
        
    Returns:
        splits: Dictionary with train/val/test episode IDs
    """
    rng = np.random.default_rng(seed)
    indices = np.arange(num_episodes)
    rng.shuffle(indices)
    
    n_train = int(num_episodes * train_ratio)
    n_val = int(num_episodes * val_ratio)
    
    train_ids = sorted(indices[:n_train].tolist())
    val_ids = sorted(indices[n_train:n_train+n_val].tolist())
    test_ids = sorted(indices[n_train+n_val:].tolist())
    
    return {
        'train': train_ids,
        'val': val_ids,
        'test': test_ids,
    }


def generate_dataset(
    num_episodes: int,
    output_dir: str,
    frames_per_episode: int = 10,
    defect_config: dict = None,
    seed: int = 42,
):
    """
    Generate complete ViDEC-Inspect dataset with proper protocol.
    
    IMPROVEMENTS FROM V1:
    - Saves random seed
    - Saves config snapshot
    - Generates train/val/test splits
    - Proper file structure
    """
    print("=" * 70)
    print("ViDEC-Inspect v0.1 Dataset Generation (REVISED P1)")
    print("=" * 70)
    print(f"Mode: PLACEHOLDER (synthetic data until HoloOcean integration)")
    print(f"Output: {output_dir}")
    print(f"Episodes: {num_episodes}")
    print(f"Frames/episode: {frames_per_episode}")
    print(f"Total frames: {num_episodes * frames_per_episode}")
    print(f"Random seed: {seed}")
    print("=" * 70)
    
    # Set global seed
    np.random.seed(seed)
    
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
            seed=seed,
        )
    
    # Generate splits
    splits = generate_splits(num_episodes, seed=seed, train_ratio=0.7, val_ratio=0.15)
    
    splits_dir = Path(output_dir) / "splits"
    ensure_dir(str(splits_dir))
    
    save_json({'episode_ids': splits['train']}, str(splits_dir / "train.json"))
    save_json({'episode_ids': splits['val']}, str(splits_dir / "val.json"))
    save_json({'episode_ids': splits['test']}, str(splits_dir / "test.json"))
    
    # Save dataset summary
    total_frames = num_episodes * frames_per_episode
    summary = {
        "benchmark_name": benchmark_config.benchmark_name,
        "benchmark_version": benchmark_config.benchmark_version,
        "dataset_version": "v0.1_placeholder",
        "data_source": "placeholder_synthetic",
        "holoocean_integrated": False,  # TODO: Change to True when HoloOcean is integrated
        "num_episodes": num_episodes,
        "frames_per_episode": frames_per_episode,
        "total_frames": total_frames,
        "random_seed": seed,
        "defect_config": defect_config,
        "annotation_layers": ["detection", "geometry", "metrology", "verification"],
        "sensors": ["RGB", "Depth"],
        "splits": {
            "train": len(splits['train']),
            "val": len(splits['val']),
            "test": len(splits['test']),
        },
    }
    
    summary_path = Path(output_dir) / "dataset_summary.json"
    save_json(summary, str(summary_path))
    
    # Save full config snapshot
    config_path = Path(output_dir) / "benchmark_config_snapshot.json"
    save_json(benchmark_config.get_config(), str(config_path))
    
    print("\n" + "=" * 70)
    print("✓ Dataset generation complete!")
    print(f"✓ {total_frames} frames in {num_episodes} episodes")
    print(f"✓ Splits: train={len(splits['train'])}, val={len(splits['val'])}, test={len(splits['test'])}")
    print(f"✓ Output: {output_dir}")
    print(f"✓ Summary: {summary_path}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Generate ViDEC-Inspect v0.1 benchmark dataset (REVISED P1)"
    )
    
    parser.add_argument('--num_episodes', type=int, default=10)
    parser.add_argument('--frames_per_episode', type=int, default=10)
    parser.add_argument('--output', type=str, default='data/raw/v01_p1')
    parser.add_argument('--num_cracks', type=int, default=1)
    parser.add_argument('--num_spalls', type=int, default=1)
    parser.add_argument('--num_negatives', type=int, default=1)
    parser.add_argument('--seed', type=int, default=42)
    
    args = parser.parse_args()
    
    defect_config = {
        'num_cracks': args.num_cracks,
        'num_spalls': args.num_spalls,
        'num_negatives': args.num_negatives,
    }
    
    generate_dataset(
        num_episodes=args.num_episodes,
        output_dir=args.output,
        frames_per_episode=args.frames_per_episode,
        defect_config=defect_config,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
