# Quick Decision Guide

## Current Status
- HoloOcean teleport: Works but robot not moving to correct pose
- Placeholder mode: Works perfectly
- All annotations: Ready

## Your Choices:

### A) Fix HoloOcean Now (2-4 hours)
Try PierHarbor world instead of SimpleUnderwater

### B) Use Placeholder Mode (30 min) - RECOMMENDED
Generate full dataset now, fix HoloOcean later in v0.2

## Recommendation: Choose B

Why?
- Benchmark value is in architecture + annotations, not simulator
- Placeholder sufficient for v0.1 and paper
- Can move forward immediately
- HoloOcean can be v0.2 feature

## Quick Commands:

Option A (try PierHarbor):
```bash
sed -i 's/SimpleUnderwater/PierHarbor/' configs/scenarios/holoocean_smoke_flatwall.py
conda activate holoocean  
python scripts/test_holoocean_with_teleport.py
```

Option B (generate dataset):
```bash
python scripts/generate_dataset_v2.py \
  --data_source placeholder \
  --num_episodes 10 \
  --frames_per_episode 10 \
  --output data/raw/v01_full \
  --seed 42
```

Choose A or B?
