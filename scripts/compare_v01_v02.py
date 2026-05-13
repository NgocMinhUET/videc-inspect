"""
Compare v0.1 placeholder dataset to v0.2 physics-aware dataset.

Aggregates low-level image statistics, quality scores, ambiguity scores,
verification status, and class/severity distributions from both datasets.

Usage:
    python scripts/compare_v01_v02.py \
        --v01 data/raw/v01_full \
        --v02 data/raw/v02_physics_test \
        --output reports/v01_vs_v02_comparison.json [--plots]
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.io import load_json


def _iter_frames(root: Path):
    if not root.exists():
        return
    for ep in sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("episode_")):
        for fr in sorted(p for p in ep.iterdir() if p.is_dir() and p.name.startswith("frame_")):
            yield ep, fr


def _compute_image_stats(rgb_path: Path):
    img = cv2.imread(str(rgb_path), cv2.IMREAD_COLOR)
    if img is None:
        return None
    rgb_f = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    gray = cv2.cvtColor((rgb_f * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    mean_rgb = rgb_f.reshape(-1, 3).mean(axis=0)
    return {
        "brightness_mean": float(gray.mean()),
        "brightness_std": float(gray.std()),
        "contrast_mean": float(gray.std() / 128.0),
        "sharpness": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        "color_cast": float(np.linalg.norm(mean_rgb - mean_rgb.mean()) / np.sqrt(3)),
    }


def analyze(root: Path) -> dict:
    img_stats = defaultdict(list)
    ambiguities = []
    verif_status = Counter()
    class_counts = Counter()
    severity_counts = Counter()
    n = 0

    for ep, fr in _iter_frames(root):
        n += 1
        rgb = fr / "rgb.png"
        if rgb.exists():
            s = _compute_image_stats(rgb)
            if s:
                for k, v in s.items():
                    img_stats[k].append(v)

        det_p = fr / "annotations" / "detection.json"
        if det_p.exists():
            try:
                det = load_json(str(det_p))
                for d in det.get("defects", []):
                    class_counts[d.get("class_name", "unknown")] += 1
            except Exception:
                pass

        ver_p = fr / "annotations" / "verification.json"
        if ver_p.exists():
            try:
                ver = load_json(str(ver_p))
                for d in ver.get("defects_verification", []):
                    ambiguities.append(float(d.get("ambiguity_score", 0.0)))
                    verif_status[d.get("verification_status", "unknown")] += 1
            except Exception:
                pass

        met_p = fr / "annotations" / "metrology.json"
        if met_p.exists():
            try:
                met = load_json(str(met_p))
                for d in met.get("defects_metrology", []):
                    severity_counts[d.get("severity", "unknown")] += 1
            except Exception:
                pass

    def _summary(vals):
        if not vals:
            return None
        arr = np.asarray(vals, dtype=np.float32)
        return {
            "n": int(arr.size),
            "mean": float(arr.mean()),
            "std": float(arr.std()),
            "min": float(arr.min()),
            "max": float(arr.max()),
        }

    return {
        "num_frames": n,
        "image_stats": {k: _summary(v) for k, v in img_stats.items()},
        "ambiguity_score": _summary(ambiguities),
        "verification_status": dict(verif_status),
        "class_counts": dict(class_counts),
        "severity_counts": dict(severity_counts),
    }


def _fmt(stat):
    if stat is None:
        return "       n/a       "
    return f"{stat['mean']:.4f} \u00b1 {stat['std']:.4f}"


def _print_report(v01: dict, v02: dict, output_path: Path) -> None:
    print("=" * 78)
    print("ViDEC-Inspect: v0.1 placeholder vs v0.2 physics-aware comparison")
    print("=" * 78)
    print(f"v01 frames: {v01['num_frames']}    v02 frames: {v02['num_frames']}")
    print("-" * 78)
    print(f"{'metric':22s} {'v01':>20s}   {'v02':>20s}")
    for key in ("brightness_mean", "brightness_std", "contrast_mean",
                "sharpness", "color_cast"):
        a = v01["image_stats"].get(key)
        b = v02["image_stats"].get(key)
        print(f"{key:22s} {_fmt(a):>20s}   {_fmt(b):>20s}")
    print("-" * 78)
    print(f"ambiguity v01: {v01['ambiguity_score']}")
    print(f"ambiguity v02: {v02['ambiguity_score']}")
    print(f"verification_status v01: {v01['verification_status']}")
    print(f"verification_status v02: {v02['verification_status']}")
    print(f"class_counts v01: {v01['class_counts']}")
    print(f"class_counts v02: {v02['class_counts']}")
    print(f"severity_counts v01: {v01['severity_counts']}")
    print(f"severity_counts v02: {v02['severity_counts']}")
    print(f"\nReport written to {output_path}")


def main():
    ap = argparse.ArgumentParser(description="Compare v0.1 vs v0.2 datasets.")
    ap.add_argument("--v01", required=True, help="Path to v0.1 dataset root.")
    ap.add_argument("--v02", required=True, help="Path to v0.2 dataset root.")
    ap.add_argument("--output", default="reports/v01_vs_v02_comparison.json")
    ap.add_argument("--plots", action="store_true",
                    help="Also write bar charts (requires matplotlib).")
    args = ap.parse_args()

    v01 = analyze(Path(args.v01))
    v02 = analyze(Path(args.v02))
    report = {"v01": v01, "v02": v02}

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(report, f, indent=2)

    _print_report(v01, v02, out)

    if args.plots:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            plot_dir = out.parent / out.stem
            plot_dir.mkdir(parents=True, exist_ok=True)
            for key in ("brightness_mean", "contrast_mean", "sharpness", "color_cast"):
                a = v01["image_stats"].get(key)
                b = v02["image_stats"].get(key)
                if not (a and b):
                    continue
                fig, ax = plt.subplots(figsize=(5, 3))
                ax.bar(["v01", "v02"], [a["mean"], b["mean"]],
                       yerr=[a["std"], b["std"]], capsize=4)
                ax.set_title(key)
                fig.tight_layout()
                fig.savefig(plot_dir / f"compare_{key}.png", dpi=120)
                plt.close(fig)
            print(f"Plots written to {plot_dir}")
        except Exception as e:
            print(f"[warn] plotting failed: {e}")


if __name__ == "__main__":
    main()
