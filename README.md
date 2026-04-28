# ViDEC-Inspect v0.1

**Vision-Driven Environmental Compliance Inspection Benchmark**

## Overview

ViDEC-Inspect is a benchmark for underwater infrastructure inspection focused on verification-driven defect detection. Version 0.1 implements Phase 1: Flat Wall inspection with RGB+Depth sensing.

## Scope v0.1

* **Scene:** Flat Wall Inspection
* **Defect Types:** Crack, Spalling, Hard Negatives
* **Robot:** HoveringAUV
* **Sensors:** RGB Camera, Depth Camera, IMU, DVL
* **Tasks:**
  - T1: Detection (bbox, mask)
  - T2: Quantification (geometry, metrology)
  - T3: Verification (evidence requirements)
* **Metrics:**
  - Detection F1, Segmentation IoU
  - Crack Width MAE
  - Verification Success Rate

## Installation

```bash
# Install HoloOcean
pip install holoocean

# Install dependencies
pip install -r requirements.txt

# Download HoloOcean worlds
python -c "import holoocean; holoocean.install('OpenWater')"
```

## Quick Start

```bash
# Generate dataset
python scripts/generate_dataset.py --num_episodes 100 --output data/raw/v01

# Visualize samples
python scripts/visualize_sample.py --data_dir data/raw/v01 --episode_id 0

# Run baseline
python scripts/evaluate_baseline.py --data_dir data/raw/v01
```

## Project Structure

```
videc-inspect/
├── configs/          # Scenario and defect configurations
├── data/            # Generated datasets
├── src/             # Core modules
│   ├── scene/       # HoloOcean scenario builder
│   ├── defects/     # Defect injection
│   ├── sensors/     # Sensor capture
│   ├── annotations/ # 4-layer annotation writers
│   ├── tasks/       # T1/T2/T3 task definitions
│   ├── metrics/     # Evaluation metrics
│   └── utils/       # Utilities
└── scripts/         # Executable scripts
```

## Annotation Schema

ViDEC-Inspect uses **4-layer annotations**:

1. **Detection:** class, bbox, mask
2. **Geometry:** skeleton, centerline, contour
3. **Metrology:** length, width profile, area, severity
4. **Verification:** evidence requirements, ambiguity zones

## Citation

```
@misc{videc-inspect-v01,
  title={ViDEC-Inspect: A Verification-Driven Benchmark for Underwater Infrastructure Inspection},
  author={Your Name},
  year={2026}
}
```

## Roadmap

* **v0.1:** Flat Wall + RGB/Depth + T1/T2/T3 ✓ (current)
* **v0.2:** Multi-scene + Communication budgets
* **v0.3:** Acoustic sensing + Re-observation policy
* **v1.0:** Full benchmark + Stonefish validation
