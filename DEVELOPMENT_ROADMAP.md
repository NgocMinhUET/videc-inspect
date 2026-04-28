# ViDEC-Inspect Development Roadmap

## ✓ Completed (v0.1 Foundation)

### Project Structure
- [x] Complete directory structure
- [x] Configuration system (YAML-based)
- [x] Modular codebase organization

### Defect Generation
- [x] Crack generator with skeleton and width profile
- [x] Spalling generator with irregular contours
- [x] Hard negative generator (5 types)
- [x] Defect injector with overlap prevention
- [x] Difficulty levels (easy/medium/hard)
- [x] Severity classification

### Annotation System
- [x] 4-layer annotation architecture
- [x] Detection layer (bbox, mask, class)
- [x] Geometry layer (skeleton, contour)
- [x] Metrology layer (physical measurements)
- [x] Verification layer (evidence requirements)
- [x] Metadata layer (robot, camera, environment)
- [x] JSON schema documentation

### Data Generation
- [x] Dataset generation script
- [x] Synthetic data pipeline (temporary)
- [x] Configurable defect parameters
- [x] Episode-based organization

### Utilities
- [x] I/O utilities (JSON, paths)
- [x] Visualization tools
- [x] Depth colormap rendering

### HoloOcean Integration (Configured)
- [x] Scenario configuration (flat_wall_rgbd_v01)
- [x] Sensor setup (RGB, Depth, IMU, DVL)
- [x] Trajectory generation (lawnmower pattern)
- [x] Test scripts

### Documentation
- [x] README with overview
- [x] QUICKSTART guide
- [x] Annotation schema spec
- [x] Requirements file
- [x] .gitignore

## 🚧 Phase 1 Remaining (Days 15-30)

### Week 3 (Days 15-21): HoloOcean Integration

**Priority: HIGH**

- [ ] Replace synthetic data with real HoloOcean frames
  - [ ] Modify `generate_dataset.py` to use HoloOcean `.tick()`
  - [ ] Extract RGB from `state['FrontCamera']`
  - [ ] Extract Depth from `state['FrontDepth']`
  - [ ] Handle HoloOcean coordinate systems
  
- [ ] Create flat wall scene in HoloOcean
  - [ ] Design wall asset (6m x 3m concrete panel)
  - [ ] Add to Unreal scene
  - [ ] Test lighting variations
  - [ ] Test water clarity variations

- [ ] Implement trajectory execution
  - [ ] Move robot along waypoints
  - [ ] Capture frames at each waypoint
  - [ ] Handle camera positioning

**Output:** Real HoloOcean data with proper wall textures

### Week 4 (Days 22-30): Defect Appearance & Metrics

**Priority: HIGH**

- [ ] Improve defect rendering on real textures
  - [ ] Crack appearance (darkness, anti-aliasing)
  - [ ] Spalling appearance (depth-based shading)
  - [ ] Hard negative realism
  - [ ] Lighting-aware rendering

- [ ] Implement baseline detector
  - [ ] YOLOv8 or Mask R-CNN setup
  - [ ] Training data loader
  - [ ] Inference pipeline
  - [ ] Bbox and mask output

- [ ] Implement metrics
  - [ ] Detection: mAP, F1, IoU
  - [ ] Quantification: Crack width MAE, Spall area error
  - [ ] Verification: Success rate, confusion matrix
  - [ ] Metrics aggregation script

**Output:** Working baseline + metrics on v0.1 dataset

## 🔮 Phase 2 (Months 2-3)

### Multi-Scene Support

- [ ] Pipe inspection scene
- [ ] Dam wall scene
- [ ] Bridge pier scene
- [ ] Scene-specific defect distributions

### Communication Budget

- [ ] Frame size tracking
- [ ] Compression simulation
- [ ] Bandwidth budget enforcement
- [ ] Bytes-per-confirmed-defect metric

### Re-observation Policy

- [ ] Close-up revisit simulation
- [ ] Benefit estimation
- [ ] Policy evaluation framework

### Advanced Features

- [ ] Acoustic sensing (sonar)
- [ ] Multi-view aggregation
- [ ] Temporal consistency
- [ ] Occlusion handling

## 🎯 Phase 3 (Months 4-6)

### Stonefish Validation

- [ ] Port scenarios to Stonefish
- [ ] Compare HoloOcean vs Stonefish
- [ ] Real-world validation dataset

### Benchmark Publication

- [ ] Public leaderboard
- [ ] Documentation website
- [ ] Paper submission
- [ ] Dataset release

## 📋 Immediate Next Steps (This Week)

### Day 1-2: Test Current System

```bash
# Generate small dataset
python scripts/generate_dataset.py --num_episodes 10 --output data/raw/test_v01

# Visualize samples
python scripts/visualize_sample.py --data_dir data/raw/test_v01 --frame_id 0 --save

# Inspect annotations
cat data/raw/test_v01/frame_000000_detection.json
cat data/raw/test_v01/frame_000000_metrology.json
```

### Day 3-4: Install HoloOcean

```bash
# Install HoloOcean
pip install holoocean

# Download Ocean world
python -c "import holoocean; holoocean.install('Ocean')"

# Test scenario
python scripts/test_scenario.py
```

### Day 5-7: First HoloOcean Integration

```bash
# Modify generate_dataset.py
# Replace generate_synthetic_frame() with:
#   env = holoocean.make(scenario_cfg=scenario)
#   state = env.tick()
#   rgb = state['FrontCamera']
#   depth = state['FrontDepth']

# Test with 1 episode
python scripts/generate_dataset.py --num_episodes 1 --output data/raw/holoocean_test
```

## 🔧 Technical Debt

### High Priority
- [ ] Add unit tests for defect generators
- [ ] Add integration tests for annotation writers
- [ ] Validate JSON schema compliance
- [ ] Error handling in dataset generation

### Medium Priority
- [ ] Optimize mask rendering performance
- [ ] Parallelize episode generation
- [ ] Add progress logging
- [ ] Add resume capability

### Low Priority
- [ ] Type hints throughout codebase
- [ ] Docstring coverage
- [ ] Code style enforcement (black, flake8)

## 📊 Success Metrics v0.1

Before moving to Phase 2, verify:

- [x] Can generate 100+ episodes without errors
- [ ] Annotations pass schema validation
- [ ] Baseline detector achieves >50% mAP
- [ ] Metrics are reproducible
- [ ] Documentation is complete
- [ ] Code is clean and tested

## 🎓 Learning Resources

### HoloOcean
- Docs: https://holoocean.readthedocs.io/
- Examples: Check `holoocean/examples/`
- Scenarios: https://holoocean.readthedocs.io/en/latest/usage/scenarios.html

### Object Detection
- YOLOv8: https://github.com/ultralytics/ultralytics
- Detectron2: https://github.com/facebookresearch/detectron2

### Underwater Vision
- Papers on underwater defect detection
- Underwater image enhancement

## 🤝 Contribution Guidelines

When adding features:

1. Follow existing code structure
2. Add docstrings
3. Update relevant documentation
4. Add example usage
5. Test on small dataset first

## 📝 Notes

### Design Decisions

**Why 4-layer annotations?**
- Separates concerns (detection vs measurement vs verification)
- Enables task-specific evaluation
- Supports incremental model development

**Why synthetic data first?**
- Faster iteration during development
- No dependency on HoloOcean installation
- Easier debugging

**Why episode-based?**
- Reflects real inspection missions
- Enables temporal reasoning later
- Natural organizational unit

### Known Limitations

- Synthetic data lacks realism (temporary)
- No branching cracks yet
- Lighting model is simplified
- No water particles/turbidity
- Defect appearance is basic

These will be addressed in Phase 1 Week 3-4.

## 🎉 Celebrate Milestones

- [x] Day 1-14: v0.1 foundation complete! 🎊
- [ ] Day 30: First real HoloOcean dataset
- [ ] Day 60: Baseline achieving 60% mAP
- [ ] Month 3: Multi-scene benchmark ready
- [ ] Month 6: Paper submitted

---

**Current Status:** ✓ v0.1 Foundation Complete (Day 14)

**Next Milestone:** HoloOcean Integration (Day 21)

**Long-term Goal:** Published benchmark with leaderboard (Month 6)
