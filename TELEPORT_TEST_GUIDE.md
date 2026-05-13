# 🎯 HoloOcean Teleport Test Guide

## 📊 Current Status

**Smoke Test:** ✅ Passed (HoloOcean works)  
**Issue Found:** ⚠️ Depth values too far (33-288m, expected ~1.5m)  
**Cause:** Robot not positioned correctly (needs teleport)  

---

## 🔧 What Was Fixed

Updated `src/scene/holoocean_source.py`:

**Before:**
```python
def _step_to_observation(pose, seed):
    # Just step, no positioning
    state = self.env.step(zero_u)
    return state
```

**After:**
```python
def _step_to_observation(pose, seed):
    # Teleport to desired pose first
    location = [pose.x_m, pose.y_m, pose.z_m]
    rotation = [pose.roll_deg, pose.pitch_deg, pose.yaw_deg]
    
    self.env.teleport(
        agent_name=self.env.main_agent,
        location=location,
        rotation=rotation
    )
    
    state = self.env.step(zero_u)
    return state
```

---

## 🧪 New Test Script

**File:** `scripts/test_holoocean_with_teleport.py`

**Purpose:** Test 3 different camera poses to find optimal positioning

**Test Poses:**
1. **Close frontal:** 1.5m from wall, facing directly
2. **Medium frontal:** 3.0m from wall, facing directly
3. **Angled view:** 2.2m from wall, 15° angle

---

## 🚀 How to Run

### Step 1: Activate Environment
```bash
conda activate holoocean
```

### Step 2: Run Teleport Test
```bash
python scripts/test_holoocean_with_teleport.py
```

**This will:**
- Show HoloOcean viewport (visual feedback)
- Test 3 different poses
- Save RGB + Depth for each
- Report depth statistics

---

## ✅ What to Check

For each pose, look for:

1. **Depth range:** Should see values 1-10m (not 30-300m)
2. **Close pixels:** Should have >10% pixels < 10m
3. **Visual:** RGB should show wall/structure

**Good result example:**
```
Depth min: 1.2 m
Depth mean (< 100m): 2.5 m
Pixels < 10m: 45.3%
```

**Bad result example:**
```
Depth min: 33.2 m
Depth mean (< 100m): 288.5 m
Pixels < 10m: 0.0%
```

---

## 🎯 Expected Outcomes

### Scenario A: One pose works ✅
- Depth values reasonable (1-5m range)
- Wall visible in RGB
- **Action:** Use that pose config in dataset generation

### Scenario B: All poses too far ⚠️
- All depths > 30m
- No wall visible
- **Possible causes:**
  1. Scene has no wall at those coordinates
  2. Y-axis direction wrong (try negative Y values)
  3. Need different HoloOcean world

### Scenario C: Teleport doesn't work ❌
- Error: "teleport not available"
- **Action:** May need different HoloOcean version or control method

---

## 🔍 Debugging Tips

### If teleport fails:
```python
# Check HoloOcean version
import holoocean
print(holoocean.__version__)

# Check available methods
env = holoocean.make(...)
print(dir(env))
```

### If depths still wrong:
```python
# Try different coordinates
# Y=0 might be wall, robot should be Y<0 (in front of wall)
pose = CapturePose(x_m=0, y_m=-2.0, z_m=-2.0, yaw_deg=90.0)

# Or try opposite direction
pose = CapturePose(x_m=0, y_m=2.0, z_m=-2.0, yaw_deg=270.0)
```

### If need to see environment:
```python
# In holoocean_source.py initialization:
HoloOceanFlatWallSource(
    scenario_cfg=SCENARIO_CFG,
    show_viewport=True,  # Enable visual
    disable_viewport_rendering=False,  # Keep rendering on
)
```

---

## 📁 Output Structure

After running test:
```
data/raw/holoocean_teleport_test/
├── close_frontal/
│   ├── rgb.png
│   ├── depth.npy
│   └── depth.png
├── medium_frontal/
│   ├── rgb.png
│   ├── depth.npy
│   └── depth.png
└── angled_view/
    ├── rgb.png
    ├── depth.npy
    └── depth.png
```

---

## 🎓 Understanding Coordinates

**HoloOcean SimpleUnderwater world (typical):**
- **X:** Horizontal (left-right)
- **Y:** Forward-backward
- **Z:** Up-down (negative = underwater)

**Typical flat wall inspection:**
```
        Y (forward)
        ↑
        |
Wall ---|--- Y=0 (wall plane)
        |
Robot --●-- Y=-2.0 (2m in front of wall)
        |
        └──→ X (horizontal)
```

**Camera rotation:**
- `yaw=90°` → Look toward +Y (at wall if Y<0)
- `yaw=270°` → Look toward -Y
- `yaw=0°` → Look toward +X

---

## 🚀 Next Steps After Test

### If pose works:
1. Update `generate_dataset_v2.py` with working pose
2. Run: `python scripts/generate_dataset_v2.py --data_source holoocean --num_episodes 1 --frames_per_episode 3`
3. Verify defects visible on HoloOcean frames

### If pose doesn't work:
1. Report depth statistics
2. We'll adjust scenario or coordinates
3. May need custom HoloOcean world with wall

---

## 📝 Quick Command Reference

```bash
# Activate environment
conda activate holoocean

# Run teleport test (with viewport)
python scripts/test_holoocean_with_teleport.py

# Check outputs
ls -lh data/raw/holoocean_teleport_test/*/

# Analyze depth
python -c "
import numpy as np
depth = np.load('data/raw/holoocean_teleport_test/close_frontal/depth.npy')
print(f'Min: {depth.min():.2f} m')
print(f'Mean: {depth.mean():.2f} m')
print(f'Close pixels: {(depth<10).sum()}/{depth.size}')
"
```

---

**Status:** Ready to test with teleport! 🚀

**Run:**
```bash
conda activate holoocean
python scripts/test_holoocean_with_teleport.py
```
