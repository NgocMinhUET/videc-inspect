# HoloOcean Integration Status

## ✅ Status: Ready for Testing

**Date:** April 28, 2026  
**Phase:** Week 3 - HoloOcean Integration  
**Integration:** FrameSource architecture complete

---

## 📦 What's Ready

### ✅ Core Architecture
- [x] `src/scene/frame_source.py` - Abstract interface
- [x] `src/scene/placeholder_source.py` - Synthetic source (working)
- [x] `src/scene/holoocean_source.py` - Simulator source (skeleton)
- [x] `scripts/generate_dataset_v2.py` - Refactored per your update
- [x] `configs/scenarios/holoocean_smoke_flatwall.py` - Minimal test scenario

### ✅ Testing Scripts
- [x] `scripts/run_holoocean_smoke_test.py` - Smoke test (just created)

---

## 🧪 Testing Procedure

### Phase 1: Smoke Test (HoloOcean Only)

**Purpose:** Verify HoloOcean can initialize and capture one frame

**Command:**
```bash
# Activate HoloOcean environment first
conda activate holoocean

# Run smoke test
python scripts/run_holoocean_smoke_test.py
```

**Expected Output:**
```
======================================================================
HoloOcean Smoke Test
======================================================================

Initializing HoloOcean source...
Scenario: FlatWallInspection

Defining capture pose...
Defining environmental conditions...

Capturing frame from HoloOcean...
✓ Capture successful!

Saving outputs...

======================================================================
✓ Smoke test PASSED
======================================================================

Saved outputs:
  RGB:       data/raw/holoocean_smoke/rgb.png
  Depth NPY: data/raw/holoocean_smoke/depth.npy
  Depth VIS: data/raw/holoocean_smoke/depth.png

Capture info:
  Source:          holoocean_flat_wall
  RGB shape:       (1080, 1920, 3)
  Depth shape:     (1080, 1920)
  Pixel-to-meter:  0.XXXXXX
  Robot position:  [0.0, -1.5, -5.0]
  Camera distance: 1.5 m
======================================================================
```

**What to Check:**
- ✅ HoloOcean environment launches
- ✅ No sensor key errors (`FrontRGB`, `FrontDepth`)
- ✅ RGB image saved correctly
- ✅ Depth map saved correctly
- ✅ Pixel-to-meter ratio calculated

**Common Issues:**

#### Issue 1: HoloOcean Not Installed
```
ModuleNotFoundError: No module named 'holoocean'
```
**Fix:**
```bash
conda activate holoocean
pip install holoocean
```

#### Issue 2: Sensor Name Mismatch
```
KeyError: 'FrontRGB'
```
**Fix:** Check `holoocean_smoke_flatwall.py` sensor names match your HoloOcean version

#### Issue 3: Depth Payload Format
```
KeyError: 'depth'
```
**Fix:** Check `holoocean_source.py` depth extraction logic

---

### Phase 2: Placeholder Mode (Sanity Check)

**Purpose:** Verify refactored `generate_dataset_v2.py` works with placeholder

**Command:**
```bash
python scripts/generate_dataset_v2.py \
  --num_episodes 1 \
  --frames_per_episode 3 \
  --output data/raw/v01_placeholder_refactor \
  --seed 42 \
  --data_source placeholder
```

**Expected:**
- ✅ Same output as before refactoring
- ✅ 3 frames generated
- ✅ Defects injected correctly
- ✅ Annotations valid
- ✅ `data_source: "placeholder"` in summary

**Verify:**
```bash
# Check dataset summary
cat data/raw/v01_placeholder_refactor/dataset_summary.json | grep data_source

# Visualize
python scripts/visualize_sample.py \
  --data_dir data/raw/v01_placeholder_refactor \
  --episode_id 0 \
  --frame_id 0 \
  --save
```

---

### Phase 3: HoloOcean Mode (Full Integration)

**Purpose:** Generate benchmark dataset with real HoloOcean frames

**Command:**
```bash
conda activate holoocean

python scripts/generate_dataset_v2.py \
  --num_episodes 1 \
  --frames_per_episode 3 \
  --output data/raw/v01_holoocean_smoke \
  --seed 42 \
  --data_source holoocean
```

**Expected Output:**
```
======================================================================
ViDEC-Inspect v0.1 Dataset Generation (REVISED P1)
======================================================================
Mode: HOLOOCEAN (real simulator data)
Frame source: holoocean
Output: data/raw/v01_holoocean_smoke
Episodes: 1
Frames/episode: 3
Total frames: 3
Random seed: 42
======================================================================

Initializing HoloOcean source...
✓ HoloOcean environment ready

Generating episodes: 100%|██████████| 1/1 [00:XX<00:00]

[Episode 0] 'flatwall_00000' - 3 frames
  Defects: 1 cracks, 1 spalls, 1 negatives
[Episode 0] ✓ Complete

======================================================================
✓ Dataset generation complete!
✓ 3 frames in 1 episodes
✓ Splits: train=0, val=0, test=1
✓ Output: data/raw/v01_holoocean_smoke
✓ holoocean_integrated: true
======================================================================
```

**What to Check:**
- ✅ HoloOcean frames captured (not placeholder textures)
- ✅ Defects visible on real frames
- ✅ Depth maps physically consistent
- ✅ `holoocean_integrated: true` in summary
- ✅ All 5 annotation layers present

**Verify:**
```bash
# Check dataset summary
cat data/raw/v01_holoocean_smoke/dataset_summary.json | jq '.holoocean_integrated, .data_source'

# Visualize
python scripts/visualize_sample.py \
  --data_dir data/raw/v01_holoocean_smoke \
  --episode_id 0 \
  --frame_id 0 \
  --save

# Check frame quality
ls -lh data/raw/v01_holoocean_smoke/episode_00000/frame_*/rgb.png
```

---

## 🎯 Success Criteria

### Smoke Test Success:
- [x] Script created: `scripts/run_holoocean_smoke_test.py`
- [ ] HoloOcean environment launches
- [ ] One frame captured (RGB + Depth)
- [ ] No sensor errors
- [ ] Outputs saved correctly

### Placeholder Mode Success:
- [ ] Generates dataset with `--data_source placeholder`
- [ ] Output identical to pre-refactor version
- [ ] Visualization works

### HoloOcean Mode Success:
- [ ] Generates dataset with `--data_source holoocean`
- [ ] Real simulator frames (not placeholder)
- [ ] Defects on HoloOcean frames
- [ ] `holoocean_integrated: true`
- [ ] Visualization works

---

## 📊 Integration Checklist

### ✅ Completed (Your Push):
- [x] Refactored `generate_dataset_v2.py` with FrameSource
- [x] Added `--data_source` CLI argument
- [x] Created `holoocean_smoke_flatwall.py` scenario
- [x] Integrated `PlaceholderFlatWallSource`
- [x] Integrated `HoloOceanFlatWallSource`

### ✅ Completed (This Session):
- [x] Created `run_holoocean_smoke_test.py`
- [x] Verified scenario config imports

### ⏳ Pending (Your Testing):
- [ ] Run smoke test
- [ ] Verify placeholder mode works
- [ ] Verify HoloOcean mode works
- [ ] Report first errors if any

---

## 🐛 Debugging Guide

### If Smoke Test Fails:

1. **Check HoloOcean Installation:**
   ```bash
   conda activate holoocean
   python -c "import holoocean; print(holoocean.__version__)"
   ```

2. **Check Scenario Import:**
   ```bash
   python -c "from configs.scenarios.holoocean_smoke_flatwall import SCENARIO_CFG; print(SCENARIO_CFG['name'])"
   ```

3. **Test Basic HoloOcean:**
   ```python
   import holoocean
   env = holoocean.make(scenario_cfg=SCENARIO_CFG)
   for i in range(10):
       state = env.step(np.zeros(8))
       print(f"Step {i}: {list(state.keys())}")
   env.close()
   ```

### If Placeholder Mode Fails:

1. **Check FrameSource Import:**
   ```bash
   python -c "from src.scene import PlaceholderFlatWallSource; print('OK')"
   ```

2. **Check Placeholder Capture:**
   ```python
   from src.scene import PlaceholderFlatWallSource, CapturePose, CaptureConditions
   source = PlaceholderFlatWallSource()
   pose = CapturePose(x_m=0, y_m=-1.5, z_m=-5, standoff_distance_m=1.5)
   conditions = CaptureConditions()
   result = source.capture(pose, conditions, seed=42)
   print(f"RGB: {result.rgb.shape}, Depth: {result.depth.shape}")
   ```

### If HoloOcean Mode Fails:

**Collect Full Error:**
```bash
python scripts/generate_dataset_v2.py \
  --data_source holoocean \
  --num_episodes 1 \
  --frames_per_episode 1 \
  --output data/raw/debug \
  --seed 42 \
  2>&1 | tee holoocean_error.log
```

**Send error log to me for analysis**

---

## 📝 Next Steps After Testing

### If All Tests Pass ✅:
1. Generate small HoloOcean dataset (5 episodes, 10 frames each)
2. Verify annotation quality
3. Update benchmark version to 0.2
4. Document HoloOcean setup requirements

### If Tests Fail ❌:
1. Paste full error log
2. I'll debug and provide fix
3. Iterate until working

---

## 📚 File Locations

**Testing:**
- `scripts/run_holoocean_smoke_test.py` - Smoke test
- `scripts/generate_dataset_v2.py` - Main generator
- `scripts/visualize_sample.py` - Visualization

**Configuration:**
- `configs/scenarios/holoocean_smoke_flatwall.py` - HoloOcean scenario

**Source:**
- `src/scene/frame_source.py` - Interface
- `src/scene/placeholder_source.py` - Placeholder implementation
- `src/scene/holoocean_source.py` - HoloOcean implementation

---

## 🎓 Architecture Recap

```
┌─────────────────────────────────────┐
│ generate_dataset_v2.py              │
│ (--data_source placeholder|holoocean)│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ FrameSource.capture(pose, conditions)│
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌─────────────┐  ┌─────────────┐
│Placeholder  │  │ HoloOcean   │
│(synthetic)  │  │ (simulator) │
└─────────────┘  └─────────────┘
```

**Key Benefit:** Swap sources without changing pipeline!

---

**Status:** All files ready, awaiting your smoke test results

**Next:** Run smoke test and report outcome 🚀
