"""Physics-aware procedural synthesis for ViDEC-Inspect v0.2."""

from .underwater_optics import (
    load_underwater_optics_config,
    apply_underwater_optics,
    compute_visibility_metrics,
)
from .camera_model import (
    load_camera_model_config,
    apply_camera_model,
)
from .defect_morphology import (
    load_morphology_config,
    sample_crack_morphology,
    sample_spall_morphology,
    sample_hard_negative_morphology,
)
from .material_model import (
    generate_concrete_surface,
    add_surface_roughness,
    add_subtle_biofouling,
)

__all__ = [
    "load_underwater_optics_config",
    "apply_underwater_optics",
    "compute_visibility_metrics",
    "load_camera_model_config",
    "apply_camera_model",
    "load_morphology_config",
    "sample_crack_morphology",
    "sample_spall_morphology",
    "sample_hard_negative_morphology",
    "generate_concrete_surface",
    "add_surface_roughness",
    "add_subtle_biofouling",
]
