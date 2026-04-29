"""
Validate a generated ViDEC-Inspect dataset.

This script checks:
1. Required files exist for each frame
2. Core benchmark metadata is present and consistent
3. Detection / geometry / metrology / verification layers agree on defect IDs
4. class_name values belong to the expected taxonomy
5. Referenced mask files exist
6. Split files reference valid episode IDs

Usage:
    python scripts/validate_dataset.py --data_dir data/raw/v01_full
    python scripts/validate_dataset.py --data_dir data/raw/v01_full --max_frames 20
"""

import argparse
import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np

from src.utils.io import load_json, get_frame_paths
from src.utils.config import benchmark_config


ALLOWED_DEFECT_CLASSES = {"crack", "spall"}
ALLOWED_NEGATIVE_TYPES = {
    "stain",
    "shadow",
    "texture_variation",
    "biological_growth",
    "surface_artifact",
}
REQUIRED_LAYERS = ["detection", "geometry", "metrology", "verification", "metadata"]


class DatasetValidator:
    def __init__(self, data_dir: str, max_frames: int | None = None):
        self.data_dir = Path(data_dir)
        self.max_frames = max_frames
        self.errors = []
        self.warnings = []
        self.stats = Counter()
        self.per_episode_counts = defaultdict(int)

    def error(self, message: str):
        self.errors.append(message)

    def warn(self, message: str):
        self.warnings.append(message)

    def discover_episodes(self):
        if not self.data_dir.exists():
            self.error(f"Dataset directory does not exist: {self.data_dir}")
            return []
        return sorted([p for p in self.data_dir.iterdir() if p.is_dir() and p.name.startswith("episode_")])

    def discover_frames(self, episode_dir: Path):
        return sorted([p for p in episode_dir.iterdir() if p.is_dir() and p.name.startswith("frame_")])

    def validate_header(self, data: dict, expected_layer: str, frame_id: int, episode_name: str, context: str):
        for field in ["benchmark_name", "benchmark_version", "annotation_layer", "scene_id", "episode_id", "frame_id"]:
            if field not in data:
                self.error(f"{context}: missing header field '{field}'")

        if data.get("benchmark_name") != benchmark_config.benchmark_name:
            self.error(f"{context}: benchmark_name mismatch: {data.get('benchmark_name')}")

        if data.get("benchmark_version") != benchmark_config.benchmark_version:
            self.warn(f"{context}: benchmark_version mismatch: {data.get('benchmark_version')}")

        if data.get("annotation_layer") != expected_layer:
            self.error(f"{context}: annotation_layer mismatch: expected {expected_layer}, got {data.get('annotation_layer')}")

        if data.get("frame_id") != frame_id:
            self.error(f"{context}: frame_id mismatch: expected {frame_id}, got {data.get('frame_id')}")

        if data.get("episode_id") != episode_name:
            self.error(f"{context}: episode_id mismatch: expected {episode_name}, got {data.get('episode_id')}")

    def validate_required_files(self, frame_dir: Path, paths: dict):
        for key in ["rgb", "depth_vis", "depth_npy", "metadata", "detection", "geometry", "metrology", "verification"]:
            p = Path(paths[key])
            if not p.exists():
                self.error(f"{frame_dir}: missing required file '{key}' -> {p}")

    def validate_detection_layer(self, frame_dir: Path, detection_json: dict):
        defect_ids = []
        negative_ids = []

        defects = detection_json.get("defects", [])
        negatives = detection_json.get("hard_negatives", [])

        for defect in defects:
            defect_id = defect.get("defect_id")
            class_name = defect.get("class_name")
            bbox = defect.get("bbox_xyxy")
            mask_path = defect.get("mask_path")

            if defect_id is None:
                self.error(f"{frame_dir}: detection defect missing defect_id")
                continue
            defect_ids.append(defect_id)

            if class_name not in ALLOWED_DEFECT_CLASSES:
                self.error(f"{frame_dir}: invalid detection class_name '{class_name}' for {defect_id}")

            if not isinstance(bbox, list) or len(bbox) != 4:
                self.error(f"{frame_dir}: invalid bbox_xyxy for {defect_id}")

            if mask_path is None:
                self.error(f"{frame_dir}: missing mask_path for {defect_id}")
            else:
                resolved_mask = frame_dir / mask_path
                if not resolved_mask.exists():
                    self.error(f"{frame_dir}: missing mask file for {defect_id}: {resolved_mask}")
                else:
                    mask = cv2.imread(str(resolved_mask), cv2.IMREAD_GRAYSCALE)
                    if mask is None:
                        self.error(f"{frame_dir}: could not read mask for {defect_id}: {resolved_mask}")

        for negative in negatives:
            negative_id = negative.get("negative_id")
            ntype = negative.get("type")
            if negative_id is None:
                self.error(f"{frame_dir}: hard negative missing negative_id")
                continue
            negative_ids.append(negative_id)
            if ntype not in ALLOWED_NEGATIVE_TYPES:
                self.warn(f"{frame_dir}: unexpected hard negative type '{ntype}' for {negative_id}")

        return set(defect_ids), set(negative_ids)

    def validate_geometry_layer(self, frame_dir: Path, geometry_json: dict):
        ids = []
        for item in geometry_json.get("defects_geometry", []):
            defect_id = item.get("defect_id")
            class_name = item.get("class_name")
            if defect_id is None:
                self.error(f"{frame_dir}: geometry entry missing defect_id")
                continue
            ids.append(defect_id)
            if class_name not in ALLOWED_DEFECT_CLASSES:
                self.error(f"{frame_dir}: invalid geometry class_name '{class_name}' for {defect_id}")
        return set(ids)

    def validate_metrology_layer(self, frame_dir: Path, metrology_json: dict):
        ids = []
        for item in metrology_json.get("defects_metrology", []):
            defect_id = item.get("defect_id")
            class_name = item.get("class_name")
            if defect_id is None:
                self.error(f"{frame_dir}: metrology entry missing defect_id")
                continue
            ids.append(defect_id)
            if class_name not in ALLOWED_DEFECT_CLASSES:
                self.error(f"{frame_dir}: invalid metrology class_name '{class_name}' for {defect_id}")
        return set(ids)

    def validate_verification_layer(self, frame_dir: Path, verification_json: dict):
        defect_ids = []
        negative_ids = []
        for item in verification_json.get("defects_verification", []):
            defect_id = item.get("defect_id")
            class_name = item.get("class_name")
            if defect_id is None:
                self.error(f"{frame_dir}: verification entry missing defect_id")
                continue
            defect_ids.append(defect_id)
            if class_name not in ALLOWED_DEFECT_CLASSES:
                self.error(f"{frame_dir}: invalid verification class_name '{class_name}' for {defect_id}")

        for item in verification_json.get("hard_negatives_verification", []):
            negative_id = item.get("negative_id")
            if negative_id is None:
                self.error(f"{frame_dir}: verification hard negative missing negative_id")
                continue
            negative_ids.append(negative_id)

        return set(defect_ids), set(negative_ids)

    def validate_depth(self, frame_dir: Path, depth_path: Path):
        try:
            depth = np.load(depth_path)
        except Exception as e:
            self.error(f"{frame_dir}: failed to load depth.npy: {e}")
            return

        if depth.ndim != 2:
            self.error(f"{frame_dir}: depth.npy must be 2D, got shape {depth.shape}")
            return

        if not np.isfinite(depth).all():
            self.error(f"{frame_dir}: depth.npy contains non-finite values")

        self.stats["depth_files"] += 1

    def validate_frame(self, episode_dir: Path, frame_dir: Path):
        episode_idx = int(episode_dir.name.split("_")[1])
        frame_id = int(frame_dir.name.split("_")[1])
        episode_name = f"flatwall_{episode_idx:05d}"
        paths = get_frame_paths(str(self.data_dir), episode_idx, frame_id)

        self.validate_required_files(frame_dir, paths)

        # Early return if required files missing
        if any(not Path(paths[key]).exists() for key in ["metadata", "detection", "geometry", "metrology", "verification"]):
            return

        metadata_json = load_json(paths["metadata"])
        detection_json = load_json(paths["detection"])
        geometry_json = load_json(paths["geometry"])
        metrology_json = load_json(paths["metrology"])
        verification_json = load_json(paths["verification"])

        self.validate_header(metadata_json, "metadata", frame_id, episode_name, f"{frame_dir}/metadata.json")
        self.validate_header(detection_json, "detection", frame_id, episode_name, f"{frame_dir}/annotations/detection.json")
        self.validate_header(geometry_json, "geometry", frame_id, episode_name, f"{frame_dir}/annotations/geometry.json")
        self.validate_header(metrology_json, "metrology", frame_id, episode_name, f"{frame_dir}/annotations/metrology.json")
        self.validate_header(verification_json, "verification", frame_id, episode_name, f"{frame_dir}/annotations/verification.json")

        det_defect_ids, det_negative_ids = self.validate_detection_layer(frame_dir, detection_json)
        geom_ids = self.validate_geometry_layer(frame_dir, geometry_json)
        metro_ids = self.validate_metrology_layer(frame_dir, metrology_json)
        ver_defect_ids, ver_negative_ids = self.validate_verification_layer(frame_dir, verification_json)

        if det_defect_ids != geom_ids:
            self.error(f"{frame_dir}: defect_id mismatch between detection and geometry: {det_defect_ids} vs {geom_ids}")
        if det_defect_ids != metro_ids:
            self.error(f"{frame_dir}: defect_id mismatch between detection and metrology: {det_defect_ids} vs {metro_ids}")
        if det_defect_ids != ver_defect_ids:
            self.error(f"{frame_dir}: defect_id mismatch between detection and verification: {det_defect_ids} vs {ver_defect_ids}")
        if det_negative_ids != ver_negative_ids:
            self.error(f"{frame_dir}: hard negative mismatch between detection and verification: {det_negative_ids} vs {ver_negative_ids}")

        metadata_defects = set(metadata_json.get("defect_ids_in_view", []))
        metadata_negatives = set(metadata_json.get("negative_ids_in_view", []))
        if metadata_defects != det_defect_ids:
            self.error(f"{frame_dir}: metadata defect_ids_in_view mismatch: {metadata_defects} vs {det_defect_ids}")
        if metadata_negatives != det_negative_ids:
            self.error(f"{frame_dir}: metadata negative_ids_in_view mismatch: {metadata_negatives} vs {det_negative_ids}")

        self.validate_depth(frame_dir, Path(paths["depth_npy"]))

        self.stats["frames_validated"] += 1
        self.stats["defects_total"] += len(det_defect_ids)
        self.stats["hard_negatives_total"] += len(det_negative_ids)
        self.per_episode_counts[episode_dir.name] += 1

    def validate_splits(self, episodes):
        splits_dir = self.data_dir / "splits"
        if not splits_dir.exists():
            self.warn(f"Missing splits directory: {splits_dir}")
            return

        available_episode_ids = {int(ep.name.split("_")[1]) for ep in episodes}
        for split_name in ["train", "val", "test"]:
            split_path = splits_dir / f"{split_name}.json"
            if not split_path.exists():
                self.warn(f"Missing split file: {split_path}")
                continue
            split_json = load_json(str(split_path))
            split_ids = split_json.get("episode_ids", [])
            for eid in split_ids:
                if eid not in available_episode_ids:
                    self.error(f"Split '{split_name}' references missing episode id: {eid}")
            self.stats[f"split_{split_name}_episodes"] = len(split_ids)

    def validate_summary(self):
        summary_path = self.data_dir / "dataset_summary.json"
        if not summary_path.exists():
            self.warn(f"Missing dataset summary: {summary_path}")
            return
        summary = load_json(str(summary_path))
        if summary.get("benchmark_name") != benchmark_config.benchmark_name:
            self.error(f"dataset_summary.json benchmark_name mismatch: {summary.get('benchmark_name')}")
        self.stats["summary_total_frames"] = summary.get("total_frames", -1)
        self.stats["summary_num_episodes"] = summary.get("num_episodes", -1)
        self.stats["summary_data_source"] = str(summary.get("data_source", "unknown"))

    def run(self):
        episodes = self.discover_episodes()
        if not episodes:
            if not self.errors:
                self.error(f"No episode directories found under {self.data_dir}")
            return self.report()

        frame_counter = 0
        for episode_dir in episodes:
            frame_dirs = self.discover_frames(episode_dir)
            for frame_dir in frame_dirs:
                self.validate_frame(episode_dir, frame_dir)
                frame_counter += 1
                if self.max_frames is not None and frame_counter >= self.max_frames:
                    break
            if self.max_frames is not None and frame_counter >= self.max_frames:
                break

        self.validate_splits(episodes)
        self.validate_summary()
        return self.report()

    def report(self):
        print("=" * 72)
        print("ViDEC-Inspect Dataset Validation Report")
        print("=" * 72)
        print(f"Dataset: {self.data_dir}")
        print(f"Frames validated: {self.stats.get('frames_validated', 0)}")
        print(f"Defects total: {self.stats.get('defects_total', 0)}")
        print(f"Hard negatives total: {self.stats.get('hard_negatives_total', 0)}")
        print(f"Episodes discovered: {len(self.per_episode_counts)}")

        if "summary_data_source" in self.stats:
            print(f"Dataset summary source: {self.stats['summary_data_source']}")
        if "summary_total_frames" in self.stats:
            print(f"Dataset summary total_frames: {self.stats['summary_total_frames']}")
        if "summary_num_episodes" in self.stats:
            print(f"Dataset summary num_episodes: {self.stats['summary_num_episodes']}")

        print("\nSplit stats:")
        for split_name in ["train", "val", "test"]:
            key = f"split_{split_name}_episodes"
            if key in self.stats:
                print(f"  {split_name}: {self.stats[key]} episodes")

        print("\nWarnings:")
        if self.warnings:
            for w in self.warnings[:20]:
                print(f"  [WARN] {w}")
            if len(self.warnings) > 20:
                print(f"  ... and {len(self.warnings) - 20} more warnings")
        else:
            print("  None")

        print("\nErrors:")
        if self.errors:
            for e in self.errors[:30]:
                print(f"  [ERR] {e}")
            if len(self.errors) > 30:
                print(f"  ... and {len(self.errors) - 30} more errors")
        else:
            print("  None")

        print("\nResult:")
        if self.errors:
            print(f"  FAILED with {len(self.errors)} errors and {len(self.warnings)} warnings")
            return 1
        print(f"  PASSED with {len(self.warnings)} warnings")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Validate ViDEC-Inspect dataset consistency")
    parser.add_argument("--data_dir", type=str, required=True, help="Dataset directory, e.g. data/raw/v01_full")
    parser.add_argument("--max_frames", type=int, default=None, help="Optional limit for quick validation")
    args = parser.parse_args()

    validator = DatasetValidator(data_dir=args.data_dir, max_frames=args.max_frames)
    raise SystemExit(validator.run())


if __name__ == "__main__":
    main()
