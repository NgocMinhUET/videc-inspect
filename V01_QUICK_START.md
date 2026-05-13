# ViDEC-Inspect v0.1 Quick Start

## 🎯 3 Commands to Get Started

### 1. Validate Dataset (2 min)
```bash
python scripts/validate_dataset.py --data_dir data/raw/v01_full --verbose
```

### 2. Visualize Samples (5 min)
```bash
python scripts/visualize_batch.py --data_dir data/raw/v01_full --num_samples 10
```

### 3. Freeze Release (1 min)
```bash
./scripts/freeze_dataset.sh
```

---

## 📊 What You Have

- **100 frames** with defects
- **5-layer annotations** (detection, geometry, metrology, verification, metadata)
- **Train/val/test splits** (7/1/2)
- **Reproducible** (seed=42)

---

## ✅ Next Steps

1. **Check validation results** - Should show 0 errors
2. **Review visualizations** - Check `data/raw/v01_full/preview/`
3. **Freeze dataset** - Creates `v01_release_candidate`
4. **Write paper/report** - Use v0.1 for methodology
5. **Plan v0.2** - HoloOcean integration later

---

## 🎓 For Academic Use

**You can claim:**
- ✅ Reproducible benchmark scaffold
- ✅ Multi-layer annotation schema  
- ✅ 100 annotated frames

**Note:**
- ⚠️ v0.1 = placeholder data (sufficient for methodology)
- ⚠️ HoloOcean = v0.2 (architecture ready, pose control pending)

**Recommended statement:**
> "Phase-1 benchmark with 100 frames, multi-layer annotations, and extensible architecture. Placeholder mode production-ready; real simulator integration ongoing."

---

**Status:** Production-ready for research! 🚀
