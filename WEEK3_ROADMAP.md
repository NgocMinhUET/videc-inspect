# Week 3 Roadmap: HoloOcean Integration

## ✅ Status: Architecture Ready

**Completed:**
- ✅ P2 fixes all applied (writers, generators, injector)
- ✅ `visualize_sample.py` updated for new structure
- ✅ `FrameSource` abstraction implemented
- ✅ `PlaceholderFlatWallSource` ready
- ✅ `HoloOceanFlatWallSource` skeleton ready

**Next:** Integrate FrameSource into `generate_dataset_v2.py`

---

## 🏗️ Architecture: FrameSource Pattern

The new architecture separates **frame acquisition** from **benchmark pipeline**:

```
┌─────────────────────────────────────────┐
│  generate_dataset_v2.py                 │
│  (Benchmark Pipeline)                   │
│                                         │
│  1. Create FrameSource                  │
│  2. For each episode:                   │
│     - Define pose & conditions          │
│     - capture = source.capture(...)     │
│     - Inject defects on capture.rgb     │
│     - Modify capture.depth              │
│     - Write annotations                 │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  FrameSource (Abstract Interface)       │
│  - capture(pose, conditions, seed)      │
│  - Returns: CaptureResult               │
└─────────────────────────────────────────┘
           │
           ├──────────────┬────────────────┐
           ▼              ▼                ▼
    ┌──────────┐  ┌──────────┐   ┌──────────┐
    │Placeholder│  │HoloOcean │   │Future   │
    │  Source   │  │  Source  │   │Simulator│
    └──────────┘  └──────────┘   └──────────┘
```

**Benefits:**
1. 🔄 Easy to swap sources (placeholder ↔ HoloOcean)
2. 🧪 Debug mode with synthetic data
3. 📊 Production mode with real simulator
4. 🔌 Future-proof for other simulators

---

## 📂 New Module: `src/scene/`

### Files Created:

#### 1. `frame_source.py` - Abstract Interface
```python
class FrameSource(ABC):
    @abstractmethod
    def capture(pose, conditions, seed) -> CaptureResult
```

**Key Classes:**
- `CapturePose`: x/y/z position, roll/pitch/yaw, standoff distance, view angle
- `CaptureConditions`: water clarity, lighting, visibility
- `CaptureResult`: rgb, depth, pixel_to_meter, robot_state, camera_state

#### 2. `placeholder_source.py` - Synthetic Source
```python
class PlaceholderFlatWallSource(FrameSource):
    def capture(...) -> CaptureResult:
        # Generate synthetic RGB texture
        # Generate flat wall depth
        # Return standardized result
```

**Status:** ✅ Production-ready (wraps existing placeholder logic)

#### 3. `holoocean_source.py` - Simulator Source (Skeleton)
```python
class HoloOceanFlatWallSource(FrameSource):
    def capture(...) -> CaptureResult:
        # TODO: Move agent to pose
        # TODO: Capture FrontRGB, FrontDepth
        # Return standardized result
```

**Status:** ⏳ Skeleton only - needs pose control implementation

---

## 🔧 Integration Steps

### Step 1: Import FrameSource (5 min)
```python
# In generate_dataset_v2.py
from src.scene import (
    CapturePose,
    CaptureConditions,
    PlaceholderFlatWallSource,
    # HoloOceanFlatWallSource,  # For later
)
```

### Step 2: Initialize Source (5 min)
```python
def generate_dataset(..., data_source="placeholder"):
    # Create frame source
    if data_source == "placeholder":
        frame_source = PlaceholderFlatWallSource(frame_size=(1920, 1080))
    elif data_source == "holoocean":
        frame_source = HoloOceanFlatWallSource(
            scenario_cfg=load_holoocean_config(),
            show_viewport=False,
        )
    else:
        raise ValueError(f"Unknown data_source: {data_source}")
```

### Step 3: Replace Frame Generation (15 min)
**Old:**
```python
rgb_clean, depth_clean, pixel_to_meter_current = generate_placeholder_flat_wall_frame(
    frame_size=(1920, 1080),
    mean_distance_to_wall=standoff_current,
    view_angle_deg=view_angle,
    seed=seed + episode_id * 1000 + frame_idx
)
```

**New:**
```python
# Define pose
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

# Define conditions
conditions = CaptureConditions(
    water_clarity=condition_params["water_clarity"],
    lighting=condition_params["lighting"],
    visibility_m=8.5,
    artificial_light=True,
    ambient_illumination_lux=300.0,
)

# Capture
capture = frame_source.capture(
    pose=pose,
    conditions=conditions,
    seed=seed + episode_id * 1000 + frame_idx,
)

# Extract
rgb_clean = capture.rgb
depth_clean = capture.depth
pixel_to_meter_current = capture.pixel_to_meter
robot_state = capture.robot_state
camera_state = capture.camera_state
```

### Step 4: Update Metadata (5 min)
```python
metadata_json = write_metadata_json(
    frame_id=frame_id,
    episode_id=episode_str,
    scene_id=scene_id,
    timestamp_sec=frame_idx * 0.2,
    robot_state=robot_state,  # From capture
    camera_state=camera_state,  # From capture
    environment={
        "water_clarity": conditions.water_clarity,
        "visibility_m": conditions.visibility_m,
        "lighting": conditions.lighting,
        "ambient_illumination_lux": conditions.ambient_illumination_lux,
        "artificial_light": conditions.artificial_light,
    },
    defect_ids=defect_ids,
    negative_ids=negative_ids,
)
```

### Step 5: Cleanup (5 min)
```python
def generate_dataset(...):
    # ... dataset generation ...
    
    # Cleanup
    frame_source.close()
```

---

## 🧪 Testing Strategy

### Phase 1: Placeholder Mode (Current)
```bash
python scripts/generate_dataset_v2.py \
    --num_episodes 2 \
    --frames_per_episode 2 \
    --output data/raw/test_framesource \
    --seed 42 \
    --data_source placeholder
```

**Expected:** Same output as current implementation

### Phase 2: HoloOcean Mode (After Integration)
```bash
python scripts/generate_dataset_v2.py \
    --num_episodes 2 \
    --frames_per_episode 2 \
    --output data/raw/test_holoocean \
    --seed 42 \
    --data_source holoocean
```

**Expected:** Real HoloOcean frames with defects

---

## 🎯 HoloOcean Integration Challenges

### Challenge 1: Pose Control
**Problem:** How to position AUV at exact pose?

**Options:**
1. **Teleport:** `env.teleport(agent, location, rotation)` (if available)
2. **PID Controller:** Drive agent to target pose
3. **Fixed Waypoints:** Pre-defined inspection trajectory

**Recommendation:** Start with teleport if available, fall back to waypoints

### Challenge 2: Sensor Names
**Current Assumption:**
- RGB sensor: `"FrontRGB"`
- Depth sensor: `"FrontDepth"`

**Action:** Verify sensor names in your HoloOcean scenario config

### Challenge 3: Depth Format
**Current Assumption:**
```python
depth_payload = state["FrontDepth"]  # dict
depth = depth_payload["depth"]  # numpy array
```

**Action:** Verify depth payload structure

### Challenge 4: Pixel-to-Meter Ratio
**Current:** Approximation from FOV
```python
fov_deg = 90.0  # TODO: Get from HoloOcean camera config
```

**Action:** Extract actual camera intrinsics from HoloOcean

---

## 📋 Week 3 Checklist

### ✅ Completed (Before Integration)
- [x] Fix `visualize_sample.py` for new structure
- [x] Create `FrameSource` abstract interface
- [x] Create `PlaceholderFlatWallSource`
- [x] Create `HoloOceanFlatWallSource` skeleton
- [x] Test imports

### ⏳ TODO (Integration Phase)
- [ ] Refactor `generate_dataset_v2.py` to use FrameSource
- [ ] Add `--data_source` CLI argument
- [ ] Test with placeholder mode (sanity check)
- [ ] Implement HoloOcean pose control
- [ ] Test with HoloOcean mode
- [ ] Update `holoocean_integrated: true` in dataset summary
- [ ] Document HoloOcean scenario requirements

### 🔮 Future (Post-Week 3)
- [ ] Advanced pose control (PID, waypoints)
- [ ] Camera intrinsics from HoloOcean
- [ ] Multiple camera support
- [ ] Sonar integration
- [ ] Dynamic lighting conditions

---

## 📚 Related Files

**Modified:**
- `scripts/visualize_sample.py` - Updated for new API

**Created:**
- `src/scene/frame_source.py` - Abstract interface
- `src/scene/placeholder_source.py` - Synthetic source
- `src/scene/holoocean_source.py` - Simulator source (skeleton)
- `src/scene/__init__.py` - Module exports

**To Modify:**
- `scripts/generate_dataset_v2.py` - Integrate FrameSource

---

## 🎓 Design Philosophy

This architecture follows the **Strategy Pattern**:
- Define interface: `FrameSource`
- Implement strategies: Placeholder, HoloOcean, Future
- Client uses interface: `generate_dataset_v2.py`

**Benefits for Research:**
1. **Reproducibility:** Switch between sources without changing pipeline
2. **Development Speed:** Debug with fast placeholder, validate with real simulator
3. **Extensibility:** Add new simulators without rewriting benchmark
4. **Paper Quality:** Clean separation of concerns

---

## 🚀 Next Steps

**Immediate (This Week):**
1. Refactor `generate_dataset_v2.py` to use FrameSource
2. Test with placeholder mode
3. Document integration

**Short-term (Next Week):**
1. Implement HoloOcean pose control
2. Test with real simulator
3. Update benchmark version to 0.2

**Mid-term (Month 1):**
1. Validate defects on HoloOcean frames
2. Collect baseline dataset
3. Run first benchmarks

---

**Status:** Architecture ready, integration pending

**Estimated Time:** 1-2 hours for integration, 2-4 hours for HoloOcean testing

**Risk:** HoloOcean pose control may require custom scene setup
