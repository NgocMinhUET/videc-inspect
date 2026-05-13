"""
Empirical calibration of ViDEC-Inspect v0.2 priors.

This package contains the calibration framework that consumes a corpus of
real (or real-like) images and/or binary defect masks and produces:
- updated YAML configs in configs/synthesis/ and configs/morphology/
- a provenance JSON describing the calibration corpus and method.

The goal is to convert the v0.2 priors from "engineering reasonable" to
"empirically calibrated", which is the positioning required for an
academic benchmark publication.
"""

from .optics_calibration import (
    compute_image_optics_stats,
    aggregate_optics_priors,
    estimate_beta_rgb_from_image,
)
from .morphology_calibration import (
    fit_crack_morphology,
    fit_spall_morphology,
)
from .material_calibration import (
    fit_material_priors,
)
from .yaml_writer import (
    write_calibrated_optics_yaml,
    write_calibrated_crack_yaml,
    write_calibrated_spall_yaml,
)

__all__ = [
    "compute_image_optics_stats",
    "aggregate_optics_priors",
    "estimate_beta_rgb_from_image",
    "fit_crack_morphology",
    "fit_spall_morphology",
    "fit_material_priors",
    "write_calibrated_optics_yaml",
    "write_calibrated_crack_yaml",
    "write_calibrated_spall_yaml",
]
