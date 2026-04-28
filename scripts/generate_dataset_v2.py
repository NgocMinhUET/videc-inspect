"""
Dataset generation script for ViDEC-Inspect v0.1.

Now supports backend frame sources through a unified FrameSource abstraction:
- placeholder synthetic source
- HoloOcean-backed source

Usage:
    python scripts/generate_dataset_v2.py --num_episodes 10 --output data/raw/v01 --seed 42 --data_source placeholder
    python scripts/generate_dataset_v2.py --num_episodes 1 --frames_per_episode 3 --output data/raw/v01_holo --seed 42 --data_source holoocean
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np
from tqdm import tqdm

from src.defects.injector import DefectInjector
from src.annotations.writers import (
    write_detection_json,
    write_geometry_json,
    write_metrology_json,
    write_verification_json,
    write_metadata_json,
)
from src.scene import (
    CapturePose,
    CaptureConditions,
    PlaceholderFlatWallSource,
    HoloOceanFlatWallSource,
)
from src.utils import (
    save_json,
    ensure_dir,
    get_frame_paths,
    apply_spall_to_depth_map,
    apply_crack_to_depth_map,
    compute_depth_quality_metrics,
    depth_to_colormap,
    benchmark_config,
)


def build_frame_source(
    data_source: str,
    frame_size=(1920, 1080),
    scenario_cfg=None,
):
    """Build the requested frame source backend."""
    if data_source == "placeholder":
        return PlaceholderFlatWallSource(frame_size=frame_size)

    if data_source == "holoocean":
        if scenario_cfg is None:
            raise ValueError("scenario_cfg is required when data_source='holoocean'")
        return HoloOceanFlatWallSource(
            scenario_cfg=scenario_cfg,
            show_viewport=False,
            disable_viewport_rendering=True,
            warmup_steps=10,
        )

    raise ValueError(f"Unsupported data_source: {data_source}")


def generate_episode(
    episode_id: int,
    output_dir: str,
    frame_source,
    num_frames: int = 10,
    defect_params: dict = None,
    condition_params: dict = None,
    seed=None,
):
    """Generate one inspection episode using the given frame source."""
    if defect_params is None:
        defect_params = {
            "num_cracks": 1,
            "num_spalls": 1,
            "num_negatives": 1,
        }

    if condition_params is None:
        condition_params = {
            "water_clarity": "moderate",
            "lighting": "normal",
            "standoff_distance_m": 1.5,
        }

    if seed is not None:
        np.random.seed(seed + episode_id)

    episode_str = f"flatwall_{episode_id:05d}"
    scene_id = f"flat_wall_{episode_id:03d}"

    print(f"\n[Episode {episode_id}] '{episode_str}' - {num_frames} frames")

    injector = DefectInjector()
    standoff_base = condition_params["standoff_distance_m"]

    initial_pose = CapturePose(
        x_m=0.0,
        y_m=-standoff_base,
        z_m=-5.0,
        roll_deg=0.0,
        pitch_deg=0.0,
        yaw_deg=180.0,
        standoff_distance_m=standoff_base,
        view_angle_deg=0.0,
    )
    initial_conditions = CaptureConditions(
        water_clarity=condition_params["water_clarity"],
        lighting=condition_params["lighting"],
        visibility_m=8.5,
        artificial_light=True,
        ambient_illumination_lux=300.0,
    )

    initial_capture = frame_source.capture(
        pose=initial_pose,
        conditions=initial_conditions,
        seed=seed + episode_id * 1000 if seed is not None else None,
    )

    initial_rgb = initial_capture.rgb
    if initial_rgb.ndim == 3 and initial_rgb.shape[2] == 4:
        initial_rgb = initial_rgb[:, :, :3].copy()

    image_size = (initial_rgb.shape[1], initial_rgb.shape[0])
    pixel_to_meter = initial_capture.pixel_to_meter

    scene = injector.generate_scene(
        image_size=image_size,
        pixel_to_meter=pixel_to_meter,
        num_cracks=defect_params["num_cracks"],
        num_spalls=defect_params["num_spalls"],
        num_negatives=defect_params["num_negatives"],
    )

    print(
        f"  Defects: {len(scene['cracks'])} cracks, {len(scene['spalls'])} spalls, "
        f"{len(scene['negatives'])} negatives"
    )

    for frame_idx in range(num_frames):
        frame_id = episode_id * 1000 + frame_idx
        t = frame_idx / max(1, num_frames - 1)

        standoff_current = standoff_base + np.sin(t * np.pi * 2) * 0.2
        view_angle = np.sin(t * np.pi * 4) * 10.0
        x_pos = 2.0 + (t * 6.0) - 3.0

        pose = CapturePose(
            x_m=x_pos,
            y_m=-standoff_current,
            z_m=-5.0,
            roll_deg=0.0,
            pitch_deg=view_angle,
            yaw_deg=180.0,
            standoff_distance_m=standoff_current,
            view_angle_deg=view_angle,
        )
        conditions = CaptureConditions(
            water_clarity=condition_params["water_clarity"],
            lighting=condition_params["lighting"],
            visibility_m=8.5,
            artificial_light=True,
            ambient_illumination_lux=300.0,
        )

        capture = frame_source.capture(
            pose=pose,
            conditions=conditions,
            seed=seed + episode_id * 1000 + frame_idx if seed is not None else None,
        )

        rgb_clean = capture.rgb
        if rgb_clean.ndim == 3 and rgb_clean.shape[2] == 4:
            rgb_clean = rgb_clean[:, :, :3].copy()

        depth_clean = capture.depth
        pixel_to_meter_current = capture.pixel_to_meter
        robot_state = capture.robot_state
        camera_state = capture.camera_state

        rgb_with_defects = injector.composite_defects_on_image(
            base_image=rgb_clean,
            scene=scene,
        )

        depth_with_defects = apply_spall_to_depth_map(
            depth_map=depth_clean,
            spalls=scene["spalls"],
            pixel_to_meter=pixel_to_meter_current,
        )
        depth_with_defects = apply_crack_to_depth_map(
            depth_map=depth_with_defects,
            cracks=scene["cracks"],
            pixel_to_meter=pixel_to_meter_current,
        )

        paths = get_frame_paths(output_dir, episode_id, frame_id)
        ensure_dir(paths["frame_dir"])
        ensure_dir(paths["masks_dir"])

        cv2.imwrite(paths["rgb"], cv2.cvtColor(rgb_with_defects, cv2.COLOR_RGB2BGR))
        depth_vis = depth_to_colormap(depth_with_defects)
        cv2.imwrite(paths["depth_vis"], cv2.cvtColor(depth_vis, cv2.COLOR_RGB2BGR))
        np.save(paths["depth_npy"], depth_with_defects)

        depth_quality = compute_depth_quality_metrics(depth_with_defects, standoff_current)
        image_quality = {
            **depth_quality,
            "sharpness_score": 0.75,
            "contrast_score": 0.70,
        }

        detection_json = write_detection_json(
            frame_id=frame_id,
            episode_id=episode_str,
            scene_id=scene_id,
            image_size=(rgb_clean.shape[1], rgb_clean.shape[0]),
            cracks=scene["cracks"],
            spalls=scene["spalls"],
            negatives=scene["negatives"],
            masks_dir=paths["masks_dir"],
        )
        save_json(detection_json, paths["detection"])

        geometry_json = write_geometry_json(
            frame_id=frame_id,
            episode_id=episode_str,
            scene_id=scene_id,
            cracks=scene["cracks"],
            spalls=scene["spalls"],
        )
        save_json(geometry_json, paths["geometry"])

        metrology_json = write_metrology_json(
            frame_id=frame_id,
            episode_id=episode_str,
            scene_id=scene_id,
            cracks=scene["cracks"],
            spalls=scene["spalls"],
            pixel_to_meter=pixel_to_meter_current,
            mean_distance_to_wall=standoff_current,
        )
        save_json(metrology_json, paths["metrology"])

        verification_json = write_verification_json(
            frame_id=frame_id,
            episode_id=episode_str,
            scene_id=scene_id,
            cracks=scene["cracks"],
            spalls=scene["spalls"],
            negatives=scene["negatives"],
            image_quality=image_quality,
        )
        save_json(verification_json, paths["verification"])

        defect_ids = [c["defect_id"] for c in scene["cracks"]] + [s["defect_id"] for s in scene["spalls"]]
        negative_ids = [n["negative_id"] for n in scene["negatives"]]

        metadata_json = write_metadata_json(
            frame_id=frame_id,
            episode_id=episode_str,
            scene_id=scene_id,
            timestamp_sec=frame_idx * 0.2,
            robot_state=robot_state,
            camera_state=camera_state,
            environment={
                "water_clarity": conditions.water_clarity,
                "visibility_m": conditions.visibility_m,
                "lighting": conditions.lighting,
                "ambient_illumination_lux": conditions.ambient_illumination_lux,
                "artificial_light": conditions.artificial_light,
                "source_name": capture.source_name,
            },
            defect_ids=defect_ids,
            negative_ids=negative_ids,
        )
        save_json(metadata_json, paths["metadata"])

    print(f"[Episode {episode_id}] ✓ Complete")


def generate_splits(num_episodes: int, seed: int, train_ratio=0.7, val_ratio=0.15):
    """Generate reproducible train/val/test splits."""
    rng = np.random.default_rng(seed)
    indices = np.arange(num_episodes)
    rng.shuffle(indices)

    n_train = int(num_episodes * train_ratio)
    n_val = int(num_episodes * val_ratio)

    train_ids = sorted(indices[:n_train].tolist())
    val_ids = sorted(indices[n_train:n_train + n_val].tolist())
    test_ids = sorted(indices[n_train + n_val:].tolist())

    return {
        "train": train_ids,
        "val": val_ids,
        "test": test_ids,
    }


def generate_dataset(
    num_episodes: int,
    output_dir: str,
    frames_per_episode: int = 10,
    defect_config: dict = None,
    seed: int = 42,
    data_source: str = "placeholder",
):
    """Generate the ViDEC-Inspect dataset using the selected backend source."""
    print("=" * 70)
    print("ViDEC-Inspect v0.1 Dataset Generation")
    print("=" * 70)
    print(f"Data source: {data_source}")
    print(f"Output: {output_dir}")
    print(f"Episodes: {num_episodes}")
    print(f"Frames/episode: {frames_per_episode}")
    print(f"Total frames: {num_episodes * frames_per_episode}")
    print(f"Random seed: {seed}")
    print("=" * 70)

    np.random.seed(seed)
    ensure_dir(output_dir)

    if defect_config is None:
        defect_config = {
            "num_cracks": 1,
            "num_spalls": 1,
            "num_negatives": 1,
        }

    frame_size = (1920, 1080)
    scenario_cfg = None
    if data_source == "holoocean":
        from configs.scenarios.holoocean_smoke_flatwall import SCENARIO_CFG
        scenario_cfg = SCENARIO_CFG

    frame_source = build_frame_source(
        data_source=data_source,
        frame_size=frame_size,
        scenario_cfg=scenario_cfg,
    )

    try:
        for episode_id in tqdm(range(num_episodes), desc="Generating episodes"):
            generate_episode(
                episode_id=episode_id,
                output_dir=output_dir,
                frame_source=frame_source,
                num_frames=frames_per_episode,
                defect_params=defect_config,
                seed=seed,
            )
    finally:
        frame_source.close()

    splits = generate_splits(num_episodes, seed=seed, train_ratio=0.7, val_ratio=0.15)
    splits_dir = Path(output_dir) / "splits"
    ensure_dir(str(splits_dir))

    save_json({"episode_ids": splits["train"]}, str(splits_dir / "train.json"))
    save_json({"episode_ids": splits["val"]}, str(splits_dir / "val.json"))
    save_json({"episode_ids": splits["test"]}, str(splits_dir / "test.json"))

    total_frames = num_episodes * frames_per_episode
    summary = {
        "benchmark_name": benchmark_config.benchmark_name,
        "benchmark_version": benchmark_config.benchmark_version,
        "dataset_version": f"v0.1_{data_source}",
        "data_source": data_source,
        "holoocean_integrated": data_source == "holoocean",
        "num_episodes": num_episodes,
        "frames_per_episode": frames_per_episode,
        "total_frames": total_frames,
        "random_seed": seed,
        "defect_config": defect_config,
        "annotation_layers": ["detection", "geometry", "metrology", "verification"],
        "sensors": ["RGB", "Depth"],
        "splits": {
            "train": len(splits["train"]),
            "val": len(splits["val"]),
            "test": len(splits["test"]),
        },
    }

    summary_path = Path(output_dir) / "dataset_summary.json"
    save_json(summary, str(summary_path))

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
        description="Generate ViDEC-Inspect v0.1 benchmark dataset"
    )

    parser.add_argument("--num_episodes", type=int, default=10)
    parser.add_argument("--frames_per_episode", type=int, default=10)
    parser.add_argument("--output", type=str, default="data/raw/v01_p1")
    parser.add_argument("--num_cracks", type=int, default=1)
    parser.add_argument("--num_spalls", type=int, default=1)
    parser.add_argument("--num_negatives", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--data_source",
        type=str,
        default="placeholder",
        choices=["placeholder", "holoocean"],
        help="Frame source backend",
    )

    args = parser.parse_args()

    defect_config = {
        "num_cracks": args.num_cracks,
        "num_spalls": args.num_spalls,
        "num_negatives": args.num_negatives,
    }

    generate_dataset(
        num_episodes=args.num_episodes,
        output_dir=args.output,
        frames_per_episode=args.frames_per_episode,
        defect_config=defect_config,
        seed=args.seed,
        data_source=args.data_source,
    )


if __name__ == "__main__":
    main()
