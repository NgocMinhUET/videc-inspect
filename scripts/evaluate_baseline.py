"""
Baseline evaluation / benchmark statistics for ViDEC-Inspect v0.1.

This script does not train a detector. Instead, it produces a sanity-level
benchmark report from the generated annotations:
- class counts
- severity distribution
- verification status distribution
- ambiguity statistics
- per-episode counts

Usage:
    python scripts/evaluate_baseline.py --data_dir data/raw/v01_full
    python scripts/evaluate_baseline.py --data_dir data/raw/v01_full --save_json reports/v01_baseline_stats.json
"""

import argparse
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from src.utils.io import load_json


class BaselineEvaluator:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.class_counter = Counter()
        self.severity_counter = Counter()
        self.verification_counter = Counter()
        self.negative_counter = Counter()
        self.ambiguity_scores = []
        self.per_episode_frames = Counter()
        self.per_episode_defects = Counter()
        self.per_episode_negatives = Counter()
        self.failures = []

    def discover_episodes(self):
        return sorted([p for p in self.data_dir.iterdir() if p.is_dir() and p.name.startswith("episode_")])

    def discover_frames(self, episode_dir: Path):
        return sorted([p for p in episode_dir.iterdir() if p.is_dir() and p.name.startswith("frame_")])

    def process_frame(self, frame_dir: Path, episode_name: str):
        ann_dir = frame_dir / "annotations"
        detection_path = ann_dir / "detection.json"
        metrology_path = ann_dir / "metrology.json"
        verification_path = ann_dir / "verification.json"

        for p in [detection_path, metrology_path, verification_path]:
            if not p.exists():
                self.failures.append(f"Missing required file: {p}")
                return

        detection = load_json(str(detection_path))
        metrology = load_json(str(metrology_path))
        verification = load_json(str(verification_path))

        metrology_by_id = {x["defect_id"]: x for x in metrology.get("defects_metrology", [])}
        verification_by_id = {x["defect_id"]: x for x in verification.get("defects_verification", [])}

        defects = detection.get("defects", [])
        negatives = detection.get("hard_negatives", [])

        self.per_episode_frames[episode_name] += 1
        self.per_episode_defects[episode_name] += len(defects)
        self.per_episode_negatives[episode_name] += len(negatives)

        for defect in defects:
            defect_id = defect.get("defect_id")
            class_name = defect.get("class_name", "unknown")
            self.class_counter[class_name] += 1

            metro = metrology_by_id.get(defect_id, {})
            severity = metro.get("severity", "unknown")
            self.severity_counter[f"{class_name}:{severity}"] += 1

            ver = verification_by_id.get(defect_id, {})
            status = ver.get("verification_status", "unknown")
            self.verification_counter[f"{class_name}:{status}"] += 1

            ambiguity = ver.get("ambiguity_score")
            if ambiguity is not None:
                self.ambiguity_scores.append(float(ambiguity))

        for negative in negatives:
            self.negative_counter[negative.get("type", "unknown")] += 1

    def run(self):
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Dataset directory not found: {self.data_dir}")

        episodes = self.discover_episodes()
        for episode_dir in episodes:
            frames = self.discover_frames(episode_dir)
            for frame_dir in frames:
                self.process_frame(frame_dir, episode_dir.name)

        ambiguity_arr = np.array(self.ambiguity_scores, dtype=np.float32) if self.ambiguity_scores else np.array([])

        report = {
            "data_dir": str(self.data_dir),
            "num_episodes": len(episodes),
            "num_frames": int(sum(self.per_episode_frames.values())),
            "class_distribution": dict(self.class_counter),
            "severity_distribution": dict(self.severity_counter),
            "verification_distribution": dict(self.verification_counter),
            "hard_negative_distribution": dict(self.negative_counter),
            "ambiguity_statistics": {
                "count": int(len(ambiguity_arr)),
                "mean": float(np.mean(ambiguity_arr)) if len(ambiguity_arr) else None,
                "median": float(np.median(ambiguity_arr)) if len(ambiguity_arr) else None,
                "min": float(np.min(ambiguity_arr)) if len(ambiguity_arr) else None,
                "max": float(np.max(ambiguity_arr)) if len(ambiguity_arr) else None,
                "std": float(np.std(ambiguity_arr)) if len(ambiguity_arr) else None,
            },
            "per_episode": {
                episode: {
                    "frames": int(self.per_episode_frames[episode]),
                    "defects": int(self.per_episode_defects[episode]),
                    "hard_negatives": int(self.per_episode_negatives[episode]),
                }
                for episode in sorted(self.per_episode_frames.keys())
            },
            "failures": self.failures,
        }
        return report


def print_report(report: dict):
    print("=" * 72)
    print("ViDEC-Inspect Baseline Benchmark Report")
    print("=" * 72)
    print(f"Dataset: {report['data_dir']}")
    print(f"Episodes: {report['num_episodes']}")
    print(f"Frames:   {report['num_frames']}")

    print("\nClass distribution:")
    for k, v in sorted(report["class_distribution"].items()):
        print(f"  {k}: {v}")

    print("\nSeverity distribution:")
    for k, v in sorted(report["severity_distribution"].items()):
        print(f"  {k}: {v}")

    print("\nVerification distribution:")
    for k, v in sorted(report["verification_distribution"].items()):
        print(f"  {k}: {v}")

    print("\nHard negative distribution:")
    for k, v in sorted(report["hard_negative_distribution"].items()):
        print(f"  {k}: {v}")

    amb = report["ambiguity_statistics"]
    print("\nAmbiguity statistics:")
    print(f"  count:  {amb['count']}")
    print(f"  mean:   {amb['mean']}")
    print(f"  median: {amb['median']}")
    print(f"  min:    {amb['min']}")
    print(f"  max:    {amb['max']}")
    print(f"  std:    {amb['std']}")

    if report["failures"]:
        print("\nFailures:")
        for item in report["failures"][:20]:
            print(f"  - {item}")
        if len(report["failures"]) > 20:
            print(f"  ... and {len(report['failures']) - 20} more")
    else:
        print("\nFailures: none")

    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description="Compute baseline benchmark statistics for ViDEC-Inspect")
    parser.add_argument("--data_dir", type=str, required=True, help="Dataset directory, e.g. data/raw/v01_full")
    parser.add_argument("--save_json", type=str, default=None, help="Optional path to save report JSON")
    args = parser.parse_args()

    evaluator = BaselineEvaluator(args.data_dir)
    report = evaluator.run()
    print_report(report)

    if args.save_json is not None:
        save_path = Path(args.save_json)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Saved JSON report to: {save_path}")


if __name__ == "__main__":
    main()
