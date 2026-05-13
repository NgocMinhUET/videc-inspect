"""
Orchestrator: run all ViDEC-Inspect v0.2 calibration steps in one command.

This is a thin wrapper around `calibrate_optics.py` and `calibrate_morphology.py`
that produces calibrated YAMLs plus a single combined provenance report.

Typical use (with real corpora once you have them):

    python scripts/calibrate_priors.py \\
        --optics_images_dir /data/real/uieb \\
        --crack_masks_dir   /data/real/crack_masks \\
        --spall_masks_dir   /data/real/spall_masks \\
        --pixel_to_meter    0.00156 \\
        --reports_dir       reports/calibration

Smoke-test (self-calibration on v0.2 synthetic output + v0.1 procedural masks):

    python scripts/calibrate_priors.py \\
        --optics_images_dir data/raw/v02_physics_test --optics_image_glob 'rgb.png' \\
        --crack_masks_dir   data/raw/v01_full         --crack_glob 'crack_*.png' \\
        --spall_masks_dir   data/raw/v01_full         --spall_glob 'spall_*.png' \\
        --pixel_to_meter    0.00156 \\
        --source_description "v0.2/v0.1 self-calibration smoke test"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

from src.calibration.optics_calibration import (
    compute_image_optics_stats,
    aggregate_optics_priors,
)
from src.calibration.morphology_calibration import (
    fit_crack_morphology,
    fit_spall_morphology,
)
from src.calibration.yaml_writer import (
    write_calibrated_optics_yaml,
    write_calibrated_crack_yaml,
    write_calibrated_spall_yaml,
)


def _load_fallback(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _collect(root: Path, glob_pattern: str):
    if root.is_file():
        return [root]
    return sorted(root.rglob(glob_pattern))


def main():
    ap = argparse.ArgumentParser()
    # Optics
    ap.add_argument("--optics_images_dir", required=False)
    ap.add_argument("--optics_image_glob", default="*.png")
    ap.add_argument("--d_bar_m", type=float, default=2.0)
    ap.add_argument("--reference_J", type=float, nargs=3, default=(0.5, 0.5, 0.5))
    # Morphology
    ap.add_argument("--crack_masks_dir", required=False)
    ap.add_argument("--crack_glob", default="crack_*.png")
    ap.add_argument("--spall_masks_dir", required=False)
    ap.add_argument("--spall_glob", default="spall_*.png")
    ap.add_argument("--pixel_to_meter", type=float, required=True)
    # Outputs
    ap.add_argument("--reports_dir", default="reports/calibration")
    ap.add_argument("--source_description", default="Unspecified calibration corpus")
    # Optional caps
    ap.add_argument("--max_images", type=int, default=None)
    args = ap.parse_args()

    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary = {"source_description": args.source_description,
               "optics": None, "crack": None, "spall": None}

    # Optics calibration.
    if args.optics_images_dir:
        images = _collect(Path(args.optics_images_dir), args.optics_image_glob)
        if args.max_images is not None:
            images = images[:args.max_images]
        print(f"[optics] {len(images)} images")
        per_image = []
        for p in images:
            s = compute_image_optics_stats(
                str(p),
                reference_J=tuple(args.reference_J),
                d_bar_m=float(args.d_bar_m),
            )
            if s is not None:
                per_image.append(s)
        aggregated = aggregate_optics_priors(per_image, auto_bin_if_missing=True)
        fb = _load_fallback(Path("configs/synthesis/underwater_optics.yaml"))
        write_calibrated_optics_yaml(
            aggregated=aggregated,
            output_path="configs/synthesis/underwater_optics.calibrated.yaml",
            source_description=args.source_description,
            fallback_v02=fb,
        )
        with open(reports_dir / "optics_provenance.json", "w") as f:
            json.dump({"aggregated": aggregated, "n_images_used": len(per_image)},
                      f, indent=2, default=float)
        summary["optics"] = {"n_images_used": len(per_image),
                             "yaml": "configs/synthesis/underwater_optics.calibrated.yaml"}

    # Morphology calibration.
    if args.crack_masks_dir or args.spall_masks_dir:
        crack_paths = _collect(Path(args.crack_masks_dir), args.crack_glob) if args.crack_masks_dir else []
        spall_paths = _collect(Path(args.spall_masks_dir), args.spall_glob) if args.spall_masks_dir else []
        print(f"[morph] crack={len(crack_paths)}  spall={len(spall_paths)}")

        crack_fit = fit_crack_morphology(crack_paths, args.pixel_to_meter) if crack_paths else {"num_samples": 0}
        spall_fit = fit_spall_morphology(spall_paths, args.pixel_to_meter) if spall_paths else {"num_samples": 0}

        fb_crack = _load_fallback(Path("configs/morphology/crack_model.yaml"))
        fb_spall = _load_fallback(Path("configs/morphology/spall_model.yaml"))

        write_calibrated_crack_yaml(
            fit=crack_fit,
            output_path="configs/morphology/crack_model.calibrated.yaml",
            source_description=args.source_description,
            fallback_v02=fb_crack,
        )
        write_calibrated_spall_yaml(
            fit=spall_fit,
            output_path="configs/morphology/spall_model.calibrated.yaml",
            source_description=args.source_description,
            fallback_v02=fb_spall,
        )
        with open(reports_dir / "morphology_provenance.json", "w") as f:
            json.dump({"crack_fit": crack_fit, "spall_fit": spall_fit},
                      f, indent=2, default=float)

        summary["crack"] = {"n": crack_fit.get("num_samples"),
                            "yaml": "configs/morphology/crack_model.calibrated.yaml"}
        summary["spall"] = {"n": spall_fit.get("num_samples"),
                            "yaml": "configs/morphology/spall_model.calibrated.yaml"}

    with open(reports_dir / "calibration_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== Calibration summary ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
