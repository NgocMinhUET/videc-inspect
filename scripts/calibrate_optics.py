"""
Calibrate the underwater optics priors for ViDEC-Inspect v0.2.

Consumes a directory (recursively) of underwater RGB images and estimates
distributional priors for `beta_rgb`, backscatter strength, contrast scale
and blur sigma proxies. Writes a calibrated YAML and a per-image JSON.

Usage (real data, when available):
    python scripts/calibrate_optics.py \
        --images_dir /path/to/real_underwater_corpus \
        --output_yaml configs/synthesis/underwater_optics.calibrated.yaml \
        --provenance_json reports/calibration/optics_provenance.json \
        --d_bar_m 2.0

Usage (smoke-test against v0.2 synthetic output):
    python scripts/calibrate_optics.py \
        --images_dir data/raw/v02_physics_test \
        --image_glob 'rgb.png' \
        --output_yaml configs/synthesis/underwater_optics.calibrated.yaml \
        --provenance_json reports/calibration/optics_provenance.json \
        --source_description "v0.2 self-calibration smoke test"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from tqdm import tqdm

from src.calibration.optics_calibration import (
    compute_image_optics_stats,
    aggregate_optics_priors,
)
from src.calibration.yaml_writer import write_calibrated_optics_yaml


def _collect_images(images_dir: Path, glob_pattern: str):
    if images_dir.is_file():
        return [images_dir]
    return sorted(images_dir.rglob(glob_pattern))


def _load_fallback(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images_dir", required=True,
                    help="Directory (searched recursively) containing RGB images.")
    ap.add_argument("--image_glob", default="*.png",
                    help="Glob (rglob) to find images, e.g. '*.png' or 'rgb.png'.")
    ap.add_argument("--labels_csv", default=None,
                    help="Optional CSV with columns image_path,water_type. If absent, auto-bin.")
    ap.add_argument("--output_yaml",
                    default="configs/synthesis/underwater_optics.calibrated.yaml")
    ap.add_argument("--provenance_json",
                    default="reports/calibration/optics_provenance.json")
    ap.add_argument("--fallback_yaml",
                    default="configs/synthesis/underwater_optics.yaml",
                    help="v0.2 default config used as fallback for missing fields.")
    ap.add_argument("--d_bar_m", type=float, default=2.0,
                    help="Assumed representative range in meters for beta inversion.")
    ap.add_argument("--reference_J", type=float, nargs=3, default=(0.5, 0.5, 0.5),
                    help="Neutral concrete reflectance (R G B in [0,1]).")
    ap.add_argument("--percentile_low", type=float, default=10.0)
    ap.add_argument("--percentile_high", type=float, default=90.0)
    ap.add_argument("--max_images", type=int, default=None)
    ap.add_argument("--source_description", type=str,
                    default="Unspecified underwater image corpus")
    args = ap.parse_args()

    images_dir = Path(args.images_dir)
    image_paths = _collect_images(images_dir, args.image_glob)
    if args.max_images is not None:
        image_paths = image_paths[:args.max_images]
    if not image_paths:
        print(f"[error] No images found under {images_dir} with glob '{args.image_glob}'")
        sys.exit(1)

    print(f"Calibrating optics from {len(image_paths)} images under {images_dir}")
    per_image_stats = []
    for p in tqdm(image_paths, desc="optics"):
        s = compute_image_optics_stats(
            str(p),
            reference_J=tuple(args.reference_J),
            d_bar_m=float(args.d_bar_m),
        )
        if s is not None:
            per_image_stats.append(s)

    water_type_labels = None
    if args.labels_csv:
        import csv
        labels_by_path = {}
        with open(args.labels_csv, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                labels_by_path[row["image_path"]] = row.get("water_type", "unlabeled")
        water_type_labels = [labels_by_path.get(s["image_path"], "unlabeled") for s in per_image_stats]

    aggregated = aggregate_optics_priors(
        per_image_stats,
        water_type_labels=water_type_labels,
        auto_bin_if_missing=True,
        percentile_low=args.percentile_low,
        percentile_high=args.percentile_high,
    )

    fallback = _load_fallback(Path(args.fallback_yaml))
    write_calibrated_optics_yaml(
        aggregated=aggregated,
        output_path=args.output_yaml,
        source_description=args.source_description,
        fallback_v02=fallback,
    )

    prov_path = Path(args.provenance_json)
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    with open(prov_path, "w") as f:
        json.dump({"aggregated": aggregated, "n_images_used": len(per_image_stats)}, f, indent=2)

    print(f"\nWrote calibrated optics YAML to: {args.output_yaml}")
    print(f"Wrote optics provenance JSON to:  {args.provenance_json}")
    for cls, block in aggregated.get("water_types", {}).items():
        if not block:
            continue
        print(f"  [{cls:9s}] n={block.get('num_samples', 0):4d}  "
              f"beta_rgb_median={block.get('beta_rgb_median')}  "
              f"bs={block.get('backscatter_strength_range')}")


if __name__ == "__main__":
    main()
