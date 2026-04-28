# FrameSource Integration Guide

## 🎯 Goal
Integrate `FrameSource` abstraction into `generate_dataset_v2.py` without breaking existing functionality.

---

## 📝 Step-by-Step Guide

### Step 1: Add Imports

**Location:** Top of `generate_dataset_v2.py`

**Add:**
```python
from src.scene import (
    CapturePose,
    CaptureConditions,
    CaptureResult,
    PlaceholderFlatWallSource,
    HoloOceanFlatWallSource,
)
```

---

### Step 2: Add CLI Argument

**Location:** In `main()` function

**Add:**
```python
parser.add_argument(
    '--data_source',
    type=str,
    default='placeholder',
    choices=['placeholder', 'holoocean'],
    help='Frame source: placeholder (synthetic) or holoocean (simulator)'
)
```

**Pass to generate_dataset:**
```python
generate_dataset(
    output_dir=args.output,
    num_episodes=args.num_episodes,
    frames_per_episode=args.frames_per_episode,
    seed=args.seed,
    data_source=args.data_source,  # NEW
)
```

---

### Step 3: Initialize FrameSource

**Location:** Beginning of `generate_dataset()` function

**Add:**
```python
def generate_dataset(
    output_dir: str,
    num_episodes: int = 50,
    frames_per_episode: int = 10,
    seed: int = 42,
    data_source: str = 'placeholder',  # NEW
):
    """
    Generate ViDEC-Inspect dataset.
    
    Args:
        output_dir: Output directory
        num_episodes: Number of episodes
        frames_per_episode: Frames per episode
        seed: Random seed
        data_source: 'placeholder' or 'holoocean'
    """
    
    # ... existing setup code ...
    
    # Initialize frame source
    print(f"Frame source: {data_source}")
    
    if data_source == 'placeholder':
        frame_source = PlaceholderFlatWallSource(frame_size=(1920, 1080))
    elif data_source == 'holoocean':
        # TODO: Load HoloOcean config
        scenario_cfg = {
            'name': 'FlatWallInspection',
            'package_name': 'Ocean',
            'world': 'SimpleUnderwater',
            # ... your scenario config ...
        }
        frame_source = HoloOceanFlatWallSource(
            scenario_cfg=scenario_cfg,
            show_viewport=False,
            disable_viewport_rendering=True,
        )
    else:
        raise ValueError(f"Unknown data_source: {data_source}")
    
    try:
        # ... rest of dataset generation ...
        pass
    finally:
        # Always cleanup
        frame_source.close()
```

---

### Step 4: Replace Frame Generation in `generate_episode()`

**Location:** Inside `generate_episode()` function, in the frame loop

**Find this block:**
```python
# Generate placeholder frame
rgb_clean, depth_clean, pixel_to_meter_current = generate_placeholder_flat_wall_frame(
    frame_size=(1920, 1080),
    mean_distance_to_wall=standoff_current,
    view_angle_deg=view_angle,
    seed=seed + episode_id * 1000 + frame_idx
)

# Robot/camera state
robot_state = {
    "position_m": [x_pos, -standoff_current, -5.0],
    "orientation_deg": [0.0, view_angle, 180.0],
    "velocity_m_s": [0.0, 0.0, 0.0],
}

camera_state = {
    "distance_to_wall_m": standoff_current,
    "view_angle_deg": view_angle,
    "look_at_point": [x_pos, 0.0, -5.0],
}
```

**Replace with:**
```python
# Define capture pose
pose = CapturePose(
    x_m=x_pos,
    y_m=-standoff_current,
    z_m=-5.0,
    roll_deg=0.0,
    pitch_deg=view_angle,
    yaw_deg=180.0,
    standoff_distance_m=standoff_current,
    view_angle_deg=view_angle,
)

# Define environmental conditions
conditions = CaptureConditions(
    water_clarity=condition_params["water_clarity"],
    lighting=condition_params["lighting"],
    visibility_m=8.5,
    artificial_light=True,
    ambient_illumination_lux=300.0,
)

# Capture frame from source
capture = frame_source.capture(
    pose=pose,
    conditions=conditions,
    seed=seed + episode_id * 1000 + frame_idx,
)

# Extract capture result
rgb_clean = capture.rgb
depth_clean = capture.depth
pixel_to_meter_current = capture.pixel_to_meter
robot_state = capture.robot_state
camera_state = capture.camera_state
```

---

### Step 5: Update Metadata Writing

**Location:** After defect injection, before writing metadata.json

**Change:**
```python
# OLD:
environment = {
    "water_clarity": condition_params["water_clarity"],
    "visibility_m": 8.5,
    "lighting": condition_params["lighting"],
    "ambient_illumination_lux": 300.0,
    "artificial_light": True,
}

# NEW:
environment = {
    "water_clarity": conditions.water_clarity,
    "visibility_m": conditions.visibility_m,
    "lighting": conditions.lighting,
    "ambient_illumination_lux": conditions.ambient_illumination_lux,
    "artificial_light": conditions.artificial_light,
}
```

---

### Step 6: Update Dataset Summary

**Location:** In `write_dataset_summary()` call

**Add:**
```python
summary = {
    "benchmark_name": benchmark_config.benchmark_name,
    "benchmark_version": benchmark_config.benchmark_version,
    "created_at": created_at.isoformat(),
    "num_episodes": num_episodes,
    "frames_per_episode": frames_per_episode,
    "total_frames": total_frames,
    "random_seed": seed,
    "splits": splits,
    "data_source": data_source,  # NEW
    "holoocean_integrated": data_source == 'holoocean',  # NEW
    # ... rest of summary ...
}
```

---

### Step 7: Remove Old Function (Optional Cleanup)

**Location:** After confirming everything works

**Remove:**
```python
def generate_placeholder_flat_wall_frame(...):
    # This is now handled by PlaceholderFlatWallSource
    pass
```

**Why:** Logic is now in `src/scene/placeholder_source.py`

---

## 🧪 Testing

### Test 1: Placeholder Mode (Sanity Check)
```bash
# Should work exactly like before
python scripts/generate_dataset_v2.py \
    --num_episodes 2 \
    --frames_per_episode 2 \
    --output data/raw/test_integration \
    --seed 42 \
    --data_source placeholder
```

**Expected:**
- ✅ Same RGB/depth quality as before
- ✅ Same file structure
- ✅ Same annotations
- ✅ `data_source: "placeholder"` in summary

### Test 2: Visualization
```bash
python scripts/visualize_sample.py \
    --data_dir data/raw/test_integration \
    --episode_id 0 \
    --frame_id 0 \
    --save
```

**Expected:**
- ✅ Preview image created
- ✅ Defects visible
- ✅ No errors

### Test 3: HoloOcean Mode (After Pose Control)
```bash
python scripts/generate_dataset_v2.py \
    --num_episodes 1 \
    --frames_per_episode 1 \
    --output data/raw/test_holoocean \
    --seed 42 \
    --data_source holoocean
```

**Expected:**
- ✅ HoloOcean launches
- ✅ Real RGB/depth captured
- ✅ Defects injected on real frames
- ✅ `holoocean_integrated: true` in summary

---

## ⚠️ Common Issues

### Issue 1: Import Error
```
ImportError: cannot import name 'CapturePose' from 'src.scene'
```

**Fix:** Make sure `src/scene/__init__.py` exports all classes

### Issue 2: FrameSource Not Found
```
NameError: name 'frame_source' is not defined
```

**Fix:** Initialize `frame_source` before the episode loop

### Issue 3: HoloOcean Not Installed
```
ModuleNotFoundError: No module named 'holoocean'
```

**Fix:** 
```bash
pip install holoocean
```

### Issue 4: Sensor Key Error
```
KeyError: 'FrontRGB'
```

**Fix:** Check your HoloOcean scenario config - sensor names must match

---

## 📋 Checklist

**Before Integration:**
- [x] `src/scene/` module created
- [x] `PlaceholderFlatWallSource` implemented
- [x] `HoloOceanFlatWallSource` skeleton ready
- [x] Imports working

**During Integration:**
- [ ] Add imports to `generate_dataset_v2.py`
- [ ] Add `--data_source` CLI argument
- [ ] Initialize `frame_source` in `generate_dataset()`
- [ ] Replace frame generation in `generate_episode()`
- [ ] Update metadata writing
- [ ] Update dataset summary
- [ ] Add try/finally for cleanup

**After Integration:**
- [ ] Test with placeholder mode
- [ ] Compare output with pre-integration
- [ ] Test visualization
- [ ] Document changes
- [ ] (Optional) Remove old function

---

## 🎯 Success Criteria

**Integration is successful if:**
1. ✅ Placeholder mode works identically to before
2. ✅ Dataset structure unchanged
3. ✅ Annotations remain consistent
4. ✅ No regression in quality
5. ✅ Ready for HoloOcean integration

---

## 📚 Reference

**Key Files:**
- `src/scene/frame_source.py` - Interface definition
- `src/scene/placeholder_source.py` - Implementation reference
- `scripts/generate_dataset_v2.py` - Integration target

**Key Classes:**
- `CapturePose` - Position and orientation
- `CaptureConditions` - Environmental parameters
- `CaptureResult` - Standardized output
- `FrameSource` - Abstract interface

---

**Next:** After successful integration, proceed to HoloOcean pose control implementation

**Estimated Time:** 30-60 minutes for integration + testing
