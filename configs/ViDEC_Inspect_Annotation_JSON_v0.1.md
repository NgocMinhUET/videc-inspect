# ViDEC-Inspect Annotation Schema v0.1

## Overview

ViDEC-Inspect uses a **4-layer annotation architecture** to support detection, quantification, and verification tasks. Each frame has 4 separate JSON files plus masks.

## File Structure per Frame

```
frame_000123_rgb.png           # RGB image
frame_000123_depth.png         # Depth visualization
frame_000123_depth.npy         # Depth array (meters)
frame_000123_metadata.json     # Frame metadata
frame_000123_detection.json    # Layer 1: Detection
frame_000123_geometry.json     # Layer 2: Geometry
frame_000123_metrology.json    # Layer 3: Metrology
frame_000123_verification.json # Layer 4: Verification
annotations/masks/
  frame_000123_crack_0012.png  # Binary mask per defect
```

## Layer 1: Detection Annotations

**Purpose:** Support object detection and segmentation (Task T1)

**File:** `frame_XXXXXX_detection.json`

```json
{
  "frame_id": 123,
  "episode_id": "flatwall_00021",
  "image_width": 1920,
  "image_height": 1080,
  "num_defects": 2,
  "defects": [
    {
      "defect_id": "crack_0012",
      "class": "crack",
      "bbox_xyxy": [120, 88, 290, 210],
      "bbox_xywh": [120, 88, 170, 122],
      "mask_path": "annotations/masks/frame_000123_crack_0012.png",
      "mask_area_pixels": 4823,
      "confidence": 1.0
    },
    {
      "defect_id": "spall_0004",
      "class": "spalling",
      "bbox_xyxy": [450, 200, 620, 380],
      "bbox_xywh": [450, 200, 170, 180],
      "mask_path": "annotations/masks/frame_000123_spall_0004.png",
      "mask_area_pixels": 12456,
      "confidence": 1.0
    }
  ],
  "hard_negatives": [
    {
      "negative_id": "neg_0008",
      "type": "stain",
      "bbox_xyxy": [800, 300, 950, 450],
      "reason": "low_contrast_pattern"
    }
  ]
}
```

## Layer 2: Geometry Annotations

**Purpose:** Provide structural topology (skeleton, contour, branches)

**File:** `frame_XXXXXX_geometry.json`

```json
{
  "frame_id": 123,
  "defects_geometry": [
    {
      "defect_id": "crack_0012",
      "class": "crack",
      "skeleton": {
        "type": "polyline",
        "coordinates_px": [
          [121, 90],
          [130, 96],
          [145, 101],
          [160, 110],
          [180, 125],
          [200, 142],
          [220, 155]
        ],
        "length_px": 145.3,
        "num_segments": 6
      },
      "branch_points": [],
      "contour": {
        "type": "polygon",
        "coordinates_px": [
          [119, 88],
          [122, 88],
          [221, 157],
          [218, 157]
        ]
      }
    },
    {
      "defect_id": "spall_0004",
      "class": "spalling",
      "contour": {
        "type": "polygon",
        "coordinates_px": [
          [455, 205],
          [470, 202],
          [615, 210],
          [618, 375],
          [460, 378]
        ],
        "area_px": 12456,
        "perimeter_px": 720.5
      },
      "major_axis_deg": 8.5,
      "minor_axis_ratio": 0.72
    }
  ]
}
```

## Layer 3: Metrology Annotations

**Purpose:** Physical measurements in real-world units

**File:** `frame_XXXXXX_metrology.json`

```json
{
  "frame_id": 123,
  "camera_parameters": {
    "focal_length_px": 1100.0,
    "baseline_m": 0.12,
    "principal_point": [960, 540]
  },
  "mean_distance_to_wall_m": 1.52,
  "pixel_to_meter_ratio": 0.0013,
  "defects_metrology": [
    {
      "defect_id": "crack_0012",
      "class": "crack",
      "length_m": 0.189,
      "width_profile": {
        "num_measurements": 7,
        "positions_normalized": [0.0, 0.17, 0.33, 0.50, 0.67, 0.83, 1.0],
        "widths_mm": [2.1, 2.3, 2.8, 3.0, 2.7, 2.4, 2.0],
        "mean_width_mm": 2.47,
        "max_width_mm": 3.0,
        "width_std_mm": 0.34
      },
      "severity": "moderate",
      "severity_criteria": {
        "method": "width_based",
        "threshold_minor_mm": 1.0,
        "threshold_moderate_mm": 2.0,
        "threshold_severe_mm": 4.0
      }
    },
    {
      "defect_id": "spall_0004",
      "class": "spalling",
      "area_m2": 0.0162,
      "depth_mm": 8.5,
      "volume_cm3": 137.7,
      "severity": "moderate",
      "severity_criteria": {
        "method": "depth_based",
        "threshold_minor_mm": 5.0,
        "threshold_moderate_mm": 10.0,
        "threshold_severe_mm": 20.0
      }
    }
  ]
}
```

## Layer 4: Verification Annotations

**Purpose:** Define what constitutes "confirmed" defect (Task T3)

**File:** `frame_XXXXXX_verification.json`

```json
{
  "frame_id": 123,
  "defects_verification": [
    {
      "defect_id": "crack_0012",
      "class": "crack",
      "visibility": "partial",
      "occlusion_ratio": 0.15,
      "image_quality": {
        "sharpness_score": 0.78,
        "contrast_score": 0.65,
        "snr_db": 18.3
      },
      "minimal_evidence_level": "roi_plus_skeleton",
      "evidence_available": {
        "has_roi": true,
        "has_mask": true,
        "has_skeleton": true,
        "has_width_profile": true
      },
      "verification_status": "confirmed",
      "requires_closeup": true,
      "closeup_benefit": {
        "expected_improvement": "width_measurement_refinement",
        "priority": "medium"
      },
      "ambiguity_zone": false,
      "ambiguity_reason": null,
      "confusable_with": [],
      "ground_truth_confidence": 1.0
    },
    {
      "defect_id": "spall_0004",
      "class": "spalling",
      "visibility": "clear",
      "occlusion_ratio": 0.0,
      "image_quality": {
        "sharpness_score": 0.82,
        "contrast_score": 0.71,
        "snr_db": 22.1
      },
      "minimal_evidence_level": "roi_plus_area",
      "evidence_available": {
        "has_roi": true,
        "has_mask": true,
        "has_depth": true,
        "has_volume": true
      },
      "verification_status": "confirmed",
      "requires_closeup": false,
      "closeup_benefit": {
        "expected_improvement": "depth_measurement_refinement",
        "priority": "low"
      },
      "ambiguity_zone": false,
      "ambiguity_reason": null,
      "confusable_with": [],
      "ground_truth_confidence": 1.0
    }
  ],
  "hard_negatives_verification": [
    {
      "negative_id": "neg_0008",
      "type": "stain",
      "designed_to_confuse": "crack",
      "distinguishing_feature": "no_skeleton_topology",
      "verification_difficulty": "medium"
    }
  ]
}
```

## Frame Metadata

**Purpose:** Environment and robot state

**File:** `frame_XXXXXX_metadata.json`

```json
{
  "frame_id": 123,
  "episode_id": "flatwall_00021",
  "timestamp_sec": 4.1,
  "robot_state": {
    "position_m": [2.34, -1.52, -5.67],
    "orientation_deg": [0.5, -2.1, 178.3],
    "velocity_m_s": [0.12, 0.0, 0.03]
  },
  "camera_state": {
    "distance_to_wall_m": 1.52,
    "view_angle_deg": 5.3,
    "look_at_point": [2.50, 0.0, -5.65]
  },
  "environment": {
    "water_clarity": "moderate",
    "visibility_m": 8.5,
    "lighting": "low",
    "ambient_illumination_lux": 120,
    "artificial_light": true
  },
  "defect_ids_in_view": ["crack_0012", "spall_0004"],
  "negative_ids_in_view": ["neg_0008"]
}
```

## Usage Guidelines

### For Task T1 (Detection)
Use **detection.json** only:
- Bounding boxes for localization
- Masks for segmentation
- Class labels

### For Task T2 (Quantification)
Use **detection.json + geometry.json + metrology.json**:
- Skeleton for crack structure
- Width profile for crack measurement
- Area/volume for spalling

### For Task T3 (Verification)
Use **all 4 layers**:
- Detection provides candidates
- Geometry provides topology
- Metrology provides measurements
- Verification defines confirmation criteria

## Hard Negatives

Hard negatives are **non-defect patterns** designed to test false positive rates:
- Stains (look like cracks but no skeleton)
- Shadows (look like depth changes but inconsistent with geometry)
- Texture variations (look like spalling but no depth)
- Surface artifacts (paint drips, biological growth)

They have detection and verification annotations but **not** geometry/metrology.

## Severity Levels

### Crack Severity
- **Minor:** width < 1mm
- **Moderate:** 1-4mm
- **Severe:** > 4mm

### Spalling Severity
- **Minor:** depth < 5mm
- **Moderate:** 5-20mm
- **Severe:** > 20mm

## Coordinate Systems

- **Image coordinates:** Top-left origin, x-right, y-down, pixels
- **World coordinates:** Right-hand, x-forward, y-left, z-up, meters
- **Robot frame:** x-forward, y-left, z-up

## Version History

- **v0.1** (2026-04): Initial release, flat wall only, RGB+Depth
