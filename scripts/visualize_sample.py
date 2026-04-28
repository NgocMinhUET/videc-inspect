"""
Visualization script for ViDEC-Inspect dataset samples.

Updated for the new episode/frame directory structure and standardized schema.

Usage:
    python scripts/visualize_sample.py --data_dir data/raw/v01_p2 --episode_id 0 --frame_id 0
    python scripts/visualize_sample.py --data_dir data/raw/v01_p2 --episode_id 0 --frame_id 0 --save
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server environments
import matplotlib.pyplot as plt

import cv2
import numpy as np

from src.utils.io import load_json, get_frame_paths
from src.utils.vis import visualize_frame, depth_to_colormap


def visualize_sample(
    data_dir: str,
    episode_id: int,
    frame_id: int,
    save_output: bool = False,
) -> None:
    """
    Visualize a single frame with annotations.

    Args:
        data_dir: Dataset root directory
        episode_id: Episode index
        frame_id: Global frame id
        save_output: Whether to save visualization
    """
    print(f"Visualizing episode={episode_id}, frame={frame_id} from {data_dir}")

    paths = get_frame_paths(data_dir, episode_id, frame_id)

    rgb_path = Path(paths["rgb"])
    if not rgb_path.exists():
        print(f"Error: RGB image not found: {rgb_path}")
        return

    rgb_image = cv2.imread(str(rgb_path), cv2.IMREAD_COLOR)
    rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)

    depth_map = None
    depth_npy_path = Path(paths["depth_npy"])
    if depth_npy_path.exists():
        depth_map = np.load(str(depth_npy_path))

    detection_path = Path(paths["detection"])
    geometry_path = Path(paths["geometry"])
    metrology_path = Path(paths["metrology"])
    verification_path = Path(paths["verification"])
    metadata_path = Path(paths["metadata"])

    required_files = [
        detection_path,
        geometry_path,
        metrology_path,
        verification_path,
        metadata_path,
    ]
    for p in required_files:
        if not p.exists():
            print(f"Error: Missing file: {p}")
            return

    detection_json = load_json(str(detection_path))
    geometry_json = load_json(str(geometry_path))
    metrology_json = load_json(str(metrology_path))
    verification_json = load_json(str(verification_path))
    metadata_json = load_json(str(metadata_path))

    # Build lookup tables
    geometry_by_id = {
        item["defect_id"]: item for item in geometry_json.get("defects_geometry", [])
    }
    metrology_by_id = {
        item["defect_id"]: item for item in metrology_json.get("defects_metrology", [])
    }
    verification_by_id = {
        item["defect_id"]: item
        for item in verification_json.get("defects_verification", [])
    }

    defects = []
    negatives = []

    frame_dir = Path(paths["frame_dir"])

    for defect_entry in detection_json.get("defects", []):
        defect_id = defect_entry["defect_id"]
        class_name = defect_entry.get("class_name", defect_entry.get("class", "unknown"))

        # Load mask relative to frame directory
        mask = None
        rel_mask_path = defect_entry.get("mask_path")
        if rel_mask_path:
            mask_path = frame_dir / rel_mask_path
            if mask_path.exists():
                mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

        geom = geometry_by_id.get(defect_id, {})
        metro = metrology_by_id.get(defect_id, {})
        verif = verification_by_id.get(defect_id, {})

        skeleton_px = None
        if geom.get("skeleton"):
            skeleton_px = geom["skeleton"].get("coordinates_px")

        defect = {
            "defect_id": defect_id,
            "class": class_name,
            "bbox_xyxy": defect_entry["bbox_xyxy"],
            "mask": mask,
            "skeleton_px": skeleton_px,
            "severity": metro.get("severity", "unknown"),
            "verification_status": verif.get("verification_status", "unknown"),
            "ambiguity_score": verif.get("ambiguity_score", None),
            "difficulty": verif.get("verification_difficulty", "unknown"),
        }
        defects.append(defect)

    for negative_entry in detection_json.get("hard_negatives", []):
        negatives.append(
            {
                "negative_id": negative_entry["negative_id"],
                "type": negative_entry["type"],
                "bbox_xyxy": negative_entry["bbox_xyxy"],
            }
        )

    vis_image = visualize_frame(
        rgb_image=rgb_image,
        depth_map=depth_map,
        defects=defects,
        negatives=negatives,
        show_masks=True,
        show_skeletons=True,
    )

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    axes[0].imshow(rgb_image)
    axes[0].set_title("Original RGB")
    axes[0].axis("off")

    if depth_map is not None:
        depth_vis = depth_to_colormap(depth_map)
        axes[1].imshow(depth_vis)
        axes[1].set_title("Depth Map")
    else:
        axes[1].text(0.5, 0.5, "No depth map", ha="center", va="center")
        axes[1].set_title("Depth Map")
    axes[1].axis("off")

    axes[2].imshow(vis_image)
    axes[2].set_title("Annotated")
    axes[2].axis("off")

    episode_name = metadata_json.get("episode_id", f"episode_{episode_id:05d}")
    plt.suptitle(
        f"Episode {episode_name} | Frame {frame_id}",
        fontsize=14,
    )
    plt.tight_layout()

    if save_output:
        preview_dir = Path(data_dir) / "preview" / f"episode_{episode_id:05d}"
        preview_dir.mkdir(parents=True, exist_ok=True)
        output_path = preview_dir / f"frame_{frame_id:06d}_preview.png"
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved visualization to: {output_path}")
    else:
        # For interactive display (requires X server)
        try:
            plt.show()
        except Exception as e:
            print(f"Warning: Could not display plot interactively: {e}")
            print("Use --save flag to save output instead.")

    print("\n" + "=" * 72)
    print(f"Episode {episode_name} | Frame {frame_id}")
    print("=" * 72)
    print(f"Benchmark: {metadata_json.get('benchmark_name', 'unknown')} "
          f"v{metadata_json.get('benchmark_version', 'unknown')}")
    print(f"Scene ID: {metadata_json.get('scene_id', 'unknown')}")
    print(f"Timestamp: {metadata_json.get('timestamp_sec', 0.0):.2f}s")
    print(f"Number of defects: {len(defects)}")

    for defect in defects:
        ambiguity = defect["ambiguity_score"]
        ambiguity_str = f"{ambiguity:.2f}" if ambiguity is not None else "N/A"
        print(
            f"  - {defect['class']}: {defect['defect_id']} | "
            f"severity={defect['severity']} | "
            f"verification={defect['verification_status']} | "
            f"ambiguity={ambiguity_str}"
        )

    print(f"Number of hard negatives: {len(negatives)}")
    for negative in negatives:
        print(f"  - {negative['type']}: {negative['negative_id']}")

    environment = metadata_json.get("environment", {})
    print(
        "Environment: "
        f"{environment.get('water_clarity', 'unknown')}, "
        f"{environment.get('lighting', 'unknown')} lighting"
    )
    print("=" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualize ViDEC-Inspect dataset samples"
    )
    parser.add_argument(
        "--data_dir",
        type=str,
        required=True,
        help="Dataset root directory",
    )
    parser.add_argument(
        "--episode_id",
        type=int,
        required=True,
        help="Episode index, e.g. 0",
    )
    parser.add_argument(
        "--frame_id",
        type=int,
        required=True,
        help="Global frame id, e.g. 0",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save visualization to file",
    )

    args = parser.parse_args()

    visualize_sample(
        data_dir=args.data_dir,
        episode_id=args.episode_id,
        frame_id=args.frame_id,
        save_output=args.save,
    )


if __name__ == "__main__":
    main()
