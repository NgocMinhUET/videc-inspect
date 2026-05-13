"""
Calibrated YAML writers for ViDEC-Inspect v0.2 priors.

Writes calibrated configs alongside the v0.2 defaults so the calibration
output is auditable. Default behaviour writes to:
  configs/synthesis/underwater_optics.calibrated.yaml
  configs/morphology/crack_model.calibrated.yaml
  configs/morphology/spall_model.calibrated.yaml

The calibrated YAMLs share the same schema as the v0.2 defaults so they can
be dropped in directly (rename to underwater_optics.yaml etc.) once accepted.
Each calibrated YAML embeds a `calibration_provenance:` block describing the
source corpus, method, percentiles, and timestamps.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import yaml


def _now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _ensure(value, fallback):
    return value if value is not None else fallback


def _is_finite_list(seq) -> bool:
    """True iff seq is a non-empty list of finite floats."""
    if seq is None:
        return False
    try:
        import math
        return len(seq) > 0 and all(
            isinstance(v, (int, float)) and math.isfinite(v) for v in seq
        )
    except Exception:
        return False


def _coalesce(empirical, fallback, provenance_flags, key_name):
    """Return empirical if finite, else fallback. Records which path was taken."""
    if _is_finite_list(empirical):
        provenance_flags[key_name] = "empirical"
        return empirical
    provenance_flags[key_name] = "fallback_v02"
    return fallback


def write_calibrated_optics_yaml(
    aggregated: Dict,
    output_path: str,
    source_description: str,
    fallback_v02: Dict,
) -> None:
    """Write configs/synthesis/underwater_optics.calibrated.yaml.

    Args:
        aggregated: output of aggregate_optics_priors.
        output_path: where to write the YAML.
        source_description: human-readable description of the source corpus.
        fallback_v02: the v0.2 default config dict, used as fallback whenever
            a calibrated range is missing (e.g., too few samples in a class).
    """
    method = aggregated.get("method", {})
    per_class = aggregated.get("water_types", {})

    def _block_for(class_name: str) -> Dict:
        fb = fallback_v02["water_types"].get(class_name, {})
        flags: Dict[str, str] = {}
        if class_name not in per_class:
            return {**fb, "_source": "fallback_v02"}

        cls = per_class[class_name]
        beta_r = cls.get("beta_r_range")
        beta_g = cls.get("beta_g_range")
        beta_b = cls.get("beta_b_range")
        fb_beta = fb.get("beta_rgb", [0.15, 0.08, 0.04])

        beta_r_used = _coalesce(beta_r, [fb_beta[0], fb_beta[0]], flags, "beta_r")
        beta_g_used = _coalesce(beta_g, [fb_beta[1], fb_beta[1]], flags, "beta_g")
        beta_b_used = _coalesce(beta_b, [fb_beta[2], fb_beta[2]], flags, "beta_b")
        beta_lo = [beta_r_used[0], beta_g_used[0], beta_b_used[0]]
        beta_hi = [beta_r_used[1], beta_g_used[1], beta_b_used[1]]

        bs = _coalesce(
            cls.get("backscatter_strength_range"),
            fb.get("backscatter_strength"),
            flags, "backscatter_strength",
        )
        blur = _coalesce(
            cls.get("blur_sigma_proxy_range"),
            fb.get("blur_sigma"),
            flags, "blur_sigma",
        )
        contrast = _coalesce(
            cls.get("contrast_scale_range"),
            fb.get("contrast_scale"),
            flags, "contrast_scale",
        )

        return {
            "description": fb.get("description", class_name),
            "beta_rgb": [float((a + b) / 2.0) for a, b in zip(beta_lo, beta_hi)],
            "beta_rgb_range_lo": beta_lo,
            "beta_rgb_range_hi": beta_hi,
            "backscatter_color_rgb": fb.get("backscatter_color_rgb"),
            "backscatter_strength": bs,
            "blur_sigma": blur,
            "contrast_scale": contrast,
            "particle_noise_strength": fb.get("particle_noise_strength"),
            "num_calibration_samples": cls.get("num_samples", 0),
            "_field_source": flags,
        }

    doc = {
        "version": "0.2-calibrated",
        "calibration_provenance": {
            "method": "simplified image-formation inversion (no depth required)",
            "source_description": source_description,
            "timestamp_utc": _now_iso(),
            "d_bar_m": method.get("d_bar_m"),
            "reference_J": method.get("reference_J"),
            "percentile_low": method.get("percentile_low"),
            "percentile_high": method.get("percentile_high"),
            "num_images": method.get("num_images"),
            "auto_binned": method.get("auto_binned"),
            "notes": (
                "beta_rgb identifiable only up to assumed d_bar; ranges are "
                "corpus-relative percentiles. Use as informed priors, not as "
                "measured constants."
            ),
        },
        "water_types": {
            "clear": _block_for("clear"),
            "moderate": _block_for("moderate"),
            "turbid": _block_for("turbid"),
        },
        "lighting": fallback_v02.get("lighting", {}),
        "clarity_alias": fallback_v02.get("clarity_alias", {}),
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)


def write_calibrated_crack_yaml(
    fit: Dict,
    output_path: str,
    source_description: str,
    fallback_v02: Dict,
) -> None:
    """Write configs/morphology/crack_model.calibrated.yaml."""
    if fit.get("num_samples", 0) == 0:
        # No samples; emit a fallback note alongside v0.2 defaults.
        doc = dict(fallback_v02)
        doc.setdefault("calibration_provenance", {})
        doc["calibration_provenance"] = {
            "method": "empirical lognormal fit (no samples available)",
            "source_description": source_description,
            "timestamp_utc": _now_iso(),
            "num_samples": 0,
            "notes": "Fallback to v0.2 engineering priors.",
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            yaml.safe_dump(doc, f, sort_keys=False)
        return

    length = fit.get("length_distribution") or {}
    width = fit.get("width_distribution") or {}
    doc = {
        "version": "0.2-calibrated",
        "class": "crack",
        "calibration_provenance": {
            "method": "skeletonization + lognormal MLE (scipy.stats.lognorm)",
            "source_description": source_description,
            "timestamp_utc": _now_iso(),
            "num_samples": fit.get("num_samples"),
            "pixel_to_meter": fit.get("pixel_to_meter"),
        },
        "length_distribution": {
            "type": "lognormal",
            "mean_log_m": length.get("mean_log", fallback_v02["length_distribution"]["mean_log_m"]),
            "std_log": length.get("std_log", fallback_v02["length_distribution"]["std_log"]),
            "clip_m": length.get("clip", fallback_v02["length_distribution"]["clip_m"]),
        },
        "width_distribution": {
            "type": "lognormal",
            "mean_log_mm": width.get("mean_log", fallback_v02["width_distribution"]["mean_log_mm"]),
            "std_log": width.get("std_log", fallback_v02["width_distribution"]["std_log"]),
            "clip_mm": width.get("clip", fallback_v02["width_distribution"]["clip_mm"]),
        },
        "tortuosity_range_empirical": fit.get("tortuosity_range"),
        "orientation_range_deg_empirical": fit.get("orientation_range_deg"),
        # Pass through v0.2 priors that are not yet calibratable from masks alone.
        "width_profile": fallback_v02.get("width_profile"),
        "tortuosity_distribution": fallback_v02.get("tortuosity_distribution"),
        "orientation_distribution": fallback_v02.get("orientation_distribution"),
        "branch_probability_by_severity": fallback_v02.get("branch_probability_by_severity"),
        "branch_count_max": fallback_v02.get("branch_count_max"),
        "branch_angle_deg": fallback_v02.get("branch_angle_deg"),
        "edge_roughness_by_severity": fallback_v02.get("edge_roughness_by_severity"),
        "contrast_range_by_severity": fallback_v02.get("contrast_range_by_severity"),
        "severity_thresholds": fallback_v02.get("severity_thresholds"),
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)


def write_calibrated_spall_yaml(
    fit: Dict,
    output_path: str,
    source_description: str,
    fallback_v02: Dict,
) -> None:
    """Write configs/morphology/spall_model.calibrated.yaml."""
    if fit.get("num_samples", 0) == 0:
        doc = dict(fallback_v02)
        doc["calibration_provenance"] = {
            "method": "empirical lognormal fit (no samples available)",
            "source_description": source_description,
            "timestamp_utc": _now_iso(),
            "num_samples": 0,
            "notes": "Fallback to v0.2 engineering priors.",
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            yaml.safe_dump(doc, f, sort_keys=False)
        return

    area = fit.get("area_distribution") or {}
    doc = {
        "version": "0.2-calibrated",
        "class": "spall",
        "calibration_provenance": {
            "method": "contour analysis + lognormal MLE",
            "source_description": source_description,
            "timestamp_utc": _now_iso(),
            "num_samples": fit.get("num_samples"),
            "pixel_to_meter": fit.get("pixel_to_meter"),
        },
        "area_distribution": {
            "type": "lognormal",
            "mean_log_m2": area.get("mean_log", fallback_v02["area_distribution"]["mean_log_m2"]),
            "std_log": area.get("std_log", fallback_v02["area_distribution"]["std_log"]),
            "clip_m2": area.get("clip", fallback_v02["area_distribution"]["clip_m2"]),
        },
        "perimeter_distribution_empirical": fit.get("perimeter_distribution"),
        "eccentricity_range_empirical": fit.get("eccentricity_range"),
        "boundary_irregularity_range_empirical": fit.get("boundary_irregularity_range"),
        # Pass through v0.2 priors that are not calibratable from masks alone.
        "depth_distribution": fallback_v02.get("depth_distribution"),
        "boundary_irregularity": fallback_v02.get("boundary_irregularity"),
        "edge_chipping": fallback_v02.get("edge_chipping"),
        "internal_roughness": fallback_v02.get("internal_roughness"),
        "depth_bowl": fallback_v02.get("depth_bowl"),
        "severity_thresholds": fallback_v02.get("severity_thresholds"),
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)
