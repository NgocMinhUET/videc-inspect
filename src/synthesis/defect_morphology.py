"""
Defect morphology sampling for ViDEC-Inspect v0.2.

Reads YAML priors and returns interpretable morphology dictionaries.
These dictionaries are intended to augment v0.1 defect generation: the
existing generators (CrackGenerator, SpallGenerator, HardNegativeGenerator)
continue to produce masks/skeletons/contours, while v0.2 morphology priors
attach calibrated severity, contrast, branching, and surface descriptors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import numpy as np
import yaml


_BASE = Path(__file__).resolve().parent.parent.parent / "configs" / "morphology"
_PATHS = {
    "crack": _BASE / "crack_model.yaml",
    "spall": _BASE / "spall_model.yaml",
    "hard_negative": _BASE / "hard_negative_model.yaml",
}


def load_morphology_config(kind: str = "all") -> Dict:
    """Load one or all morphology configs.

    Args:
        kind: 'crack' | 'spall' | 'hard_negative' | 'all'.
    """
    if kind == "all":
        return {k: yaml.safe_load(open(p)) for k, p in _PATHS.items()}
    if kind not in _PATHS:
        raise ValueError(f"Unknown morphology kind '{kind}'. Known: {list(_PATHS.keys())}")
    with open(_PATHS[kind], "r") as f:
        return yaml.safe_load(f)


def _rng(seed: Optional[int]) -> np.random.Generator:
    return np.random.default_rng(seed)


def _sample_lognormal(
    rng: np.random.Generator,
    cfg: Dict,
    key_mean: str,
    key_std: str,
    clip_key: str,
) -> float:
    mu = float(cfg[key_mean])
    sigma = float(cfg[key_std])
    val = float(rng.lognormal(mean=mu, sigma=sigma))
    lo, hi = cfg[clip_key]
    return float(np.clip(val, float(lo), float(hi)))


def _sample_uniform(rng: np.random.Generator, lo_hi) -> float:
    lo, hi = float(lo_hi[0]), float(lo_hi[1])
    if hi <= lo:
        return lo
    return float(rng.uniform(lo, hi))


def sample_crack_morphology(
    severity: Optional[str] = None,
    seed: Optional[int] = None,
) -> Dict:
    """Sample a crack morphology descriptor from the v0.2 priors."""
    cfg = load_morphology_config("crack")
    rng = _rng(seed)

    length_m = _sample_lognormal(
        rng, cfg["length_distribution"], "mean_log_m", "std_log", "clip_m"
    )
    mean_width_mm = _sample_lognormal(
        rng, cfg["width_distribution"], "mean_log_mm", "std_log", "clip_mm"
    )

    thr = cfg["severity_thresholds"]
    if severity is None:
        if mean_width_mm < float(thr["minor"]["max_width_mm"]):
            severity = "minor"
        elif mean_width_mm < float(thr["moderate"]["max_width_mm"]):
            severity = "moderate"
        else:
            severity = "severe"

    width_std_ratio = _sample_uniform(rng, cfg["width_profile"]["std_ratio_range"])

    tort_cfg = cfg["tortuosity_distribution"]
    beta_sample = float(rng.beta(float(tort_cfg["alpha"]), float(tort_cfg["beta"])))
    tortuosity = 1.0 + float(tort_cfg["scale"]) * beta_sample

    orientation_deg = _sample_uniform(rng, cfg["orientation_distribution"]["range_deg"])
    branch_p = float(cfg["branch_probability_by_severity"][severity])
    branch_count = int(rng.binomial(int(cfg["branch_count_max"]), branch_p))
    edge_roughness = _sample_uniform(rng, cfg["edge_roughness_by_severity"][severity])
    contrast = _sample_uniform(rng, cfg["contrast_range_by_severity"][severity])

    return {
        "class_name": "crack",
        "length_m": length_m,
        "mean_width_mm": mean_width_mm,
        "max_width_mm": float(mean_width_mm * (1.0 + 2.0 * width_std_ratio)),
        "width_std_ratio": width_std_ratio,
        "tortuosity": float(tortuosity),
        "orientation_deg": orientation_deg,
        "branch_probability": branch_p,
        "branch_count": branch_count,
        "edge_roughness": edge_roughness,
        "local_contrast": contrast,
        "severity": severity,
    }


def sample_spall_morphology(
    severity: Optional[str] = None,
    seed: Optional[int] = None,
) -> Dict:
    """Sample a spall morphology descriptor from the v0.2 priors."""
    cfg = load_morphology_config("spall")
    rng = _rng(seed)

    area_m2 = _sample_lognormal(
        rng, cfg["area_distribution"], "mean_log_m2", "std_log", "clip_m2"
    )
    depth_mm = _sample_lognormal(
        rng, cfg["depth_distribution"], "mean_log_mm", "std_log", "clip_mm"
    )

    thr = cfg["severity_thresholds"]
    if severity is None:
        if depth_mm < float(thr["minor"]["max_depth_mm"]):
            severity = "minor"
        elif depth_mm < float(thr["moderate"]["max_depth_mm"]):
            severity = "moderate"
        else:
            severity = "severe"

    bi = cfg["boundary_irregularity"]
    num_vertices = int(rng.integers(
        int(bi["num_vertices_range"][0]),
        int(bi["num_vertices_range"][1]) + 1,
    ))
    radial_perturb_std = _sample_uniform(rng, bi["radial_perturb_std"])

    ec = cfg["edge_chipping"]
    chipping = bool(rng.random() < float(ec["probability_by_severity"][severity]))
    notch_count = (
        int(rng.integers(int(ec["notch_count_range"][0]), int(ec["notch_count_range"][1]) + 1))
        if chipping else 0
    )

    db = cfg["depth_bowl"]
    p_exp = _sample_uniform(rng, db["shape_exponent_p_range"])
    q_exp = _sample_uniform(rng, db["shape_exponent_q_range"])

    ir = cfg["internal_roughness"]
    exposed_aggregate = bool(rng.random() < float(ir["exposed_aggregate_probability_by_severity"][severity]))
    exposed_rebar = bool(rng.random() < float(ir["exposed_rebar_probability_by_severity"][severity]))

    return {
        "class_name": "spall",
        "area_m2": area_m2,
        "depth_mm": depth_mm,
        "num_boundary_vertices": num_vertices,
        "boundary_irregularity": radial_perturb_std,
        "edge_chipping": chipping,
        "notch_count": notch_count,
        "internal_roughness": float(ir["base_amplitude"]) * (1.5 if exposed_aggregate else 1.0),
        "exposed_aggregate": exposed_aggregate,
        "exposed_rebar": exposed_rebar,
        "depth_bowl_p": p_exp,
        "depth_bowl_q": q_exp,
        "severity": severity,
    }


def sample_hard_negative_morphology(
    negative_type: str,
    seed: Optional[int] = None,
) -> Dict:
    """Sample a hard-negative descriptor from the v0.2 priors.

    'biofouling' is accepted as alias for 'biological_growth' to satisfy v0.2
    prompt vocabulary while keeping the v0.1 validator taxonomy intact.
    """
    cfg = load_morphology_config("hard_negative")
    rng = _rng(seed)

    if negative_type == "biofouling":
        negative_type = "biological_growth"

    if negative_type not in cfg["types"]:
        raise ValueError(
            f"Unknown negative_type '{negative_type}'. Known: {list(cfg['types'].keys())}"
        )

    t = cfg["types"][negative_type]
    return {
        "negative_type": negative_type,
        "coverage_area_m2": _sample_uniform(rng, t["coverage_area_m2"]),
        "edge_softness": _sample_uniform(rng, t["edge_softness"]),
        "texture_frequency": _sample_uniform(rng, t["texture_frequency"]),
        "color_shift_value": _sample_uniform(rng, t["color_shift_value"]),
        "contrast": _sample_uniform(rng, t["contrast_range"]),
        "confusability_score": _sample_uniform(rng, t["confusability_score"]),
        "confusable_with": t["confusable_with"],
    }
