# ViDEC-Inspect v0.1 Quick Start Guide

## Installation

### 1. Clone and setup

```bash
cd videc-inspect
pip install -r requirements.txt
```

### 2. (Optional) Install HoloOcean

For real simulator data (recommended later):

```bash
pip install holoocean
python -c "import holoocean; holoocean.install('Ocean')"
```

For now, the benchmark works with synthetic data.

## Generate Your First Dataset

### Quick test (2 episodes, 3 frames each)

```bash
python scripts/generate_dataset.py \
    --num_episodes 2 \
    --frames_per_episode 3 \
    --output data/raw/test
```

Expected output:
```
✓ Generated 6 frames in 2 episodes
✓ Output: data/raw/test
```

### Small benchmark (100 episodes, 10 frames each)

```bash
python scripts/generate_dataset.py \
    --num_episodes 100 \
    --frames_per_episode 10 \
    --output data/raw/v01_small
```

This will generate 1000 frames (~2-3 minutes on typical machine).

### Full v0.1 benchmark (recommended)

```bash
python scripts/generate_dataset.py \
    --num_episodes 500 \
    --frames_per_episode 10 \
    --output data/raw/v01 \
    --num_cracks 1 \
    --num_spalls 1 \
    --num_negatives 2
```

This will generate 5000 frames (~15-20 minutes).

## Visualize Samples

View a generated frame with annotations:

```bash
python scripts/visualize_sample.py \
    --data_dir data/raw/test \
    --frame_id 0 \
    --save
```

This will:
- Show RGB, depth, and annotated images
- Print defect summary
- Save visualization to `data/raw/test/preview/`

## Understand the Data Structure

Each frame has:

```
frame_000000_rgb.png           # RGB image
frame_000000_depth.png         # Depth visualization
frame_000000_depth.npy         # Depth array (meters)
frame_000000_metadata.json     # Frame metadata
frame_000000_detection.json    # Layer 1: Detection (bbox, mask)
frame_000000_geometry.json     # Layer 2: Geometry (skeleton, contour)
frame_000000_metrology.json    # Layer 3: Metrology (measurements)
frame_000000_verification.json # Layer 4: Verification (evidence)
annotations/masks/
  frame_000000_crack_0000.png  # Binary mask per defect
```

## Inspect Annotations

### Detection layer (Task T1)

```bash
cat data/raw/test/frame_000000_detection.json
```

Contains: `class`, `bbox`, `mask_path`

### Geometry layer (Task T2)

```bash
cat data/raw/test/frame_000000_geometry.json
```

Contains: `skeleton`, `contour`, crack centerline, spall shape

### Metrology layer (Task T2)

```bash
cat data/raw/test/frame_000000_metrology.json
```

Contains: `length_m`, `width_profile_mm`, `area_m2`, `depth_mm`, `severity`

### Verification layer (Task T3)

```bash
cat data/raw/test/frame_000000_verification.json
```

Contains: `minimal_evidence_level`, `requires_closeup`, `ambiguity_zone`

## Test HoloOcean Integration

```bash
python scripts/test_scenario.py
```

This will test:
- Scenario configuration
- HoloOcean integration (if installed)

## Next Steps

### 1. Customize defect generation

Edit configs:
- `configs/defects/crack.yaml` - Crack parameters
- `configs/defects/spall.yaml` - Spalling parameters
- `configs/defects/hard_negative.yaml` - Hard negative types
- `configs/conditions/env_matrix_v01.yaml` - Environmental conditions

### 2. Generate varied conditions

```bash
python scripts/generate_dataset.py \
    --num_episodes 100 \
    --output data/raw/v01_varied \
    --num_cracks 2 \
    --num_spalls 1 \
    --num_negatives 3
```

### 3. Implement baseline detector

Create `scripts/evaluate_baseline.py`:
- Load detection annotations
- Run YOLO / Mask R-CNN
- Compute mAP, F1, IoU
- Measure crack width MAE
- Calculate verification success rate

### 4. Integrate real HoloOcean scenes

Once HoloOcean is installed:
- Modify `generate_dataset.py` to use real simulator
- Replace `generate_synthetic_frame()` with HoloOcean `.tick()`
- Capture RGB and Depth from HoloOcean state
- Use real wall textures

## Troubleshooting

### Import errors

Make sure you're in the project root:
```bash
cd /home/guest/Minh/videc-inspect
```

### HoloOcean not found

If you want to use real simulator (optional for v0.1):
```bash
pip install holoocean
python -c "import holoocean; holoocean.install('Ocean')"
```

For now, synthetic data works fine for testing.

### Visualization doesn't show

Install matplotlib backend:
```bash
pip install matplotlib pillow
```

## What's Working Now

✓ Project structure
✓ Defect generation (crack, spall, hard negatives)
✓ 4-layer annotation schema
✓ Dataset generation with synthetic data
✓ Visualization
✓ HoloOcean scenario configuration

## What's Next (Phase 2)

- [ ] Multi-scene families (pipe, dam, bridge pier)
- [ ] Real HoloOcean integration with wall textures
- [ ] Communication budget tracking
- [ ] Re-observation policy
- [ ] Baseline detector implementation
- [ ] Metrics calculation
- [ ] Acoustic sensing (sonar)

## Getting Help

Check:
- `README.md` - Full documentation
- `configs/ViDEC_Inspect_Annotation_JSON_v0.1.md` - Annotation spec
- `configs/scenarios/flat_wall_rgbd_v01.py` - Scenario code
- Test files in `scripts/test_*.py`

## Citation

If you use this benchmark:

```bibtex
@misc{videc-inspect-v01,
  title={ViDEC-Inspect: A Verification-Driven Benchmark for Underwater Infrastructure Inspection},
  author={Your Name},
  year={2026}
}
```
