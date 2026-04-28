# 🚀 Quick Test Card

## ✅ Status
**Code:** Complete  
**Testing:** Your turn!

---

## 🧪 Three Commands

### 1️⃣ Smoke Test (30s)
```bash
conda activate holoocean
python scripts/run_holoocean_smoke_test.py
```

### 2️⃣ Placeholder (1-2min)
```bash
python scripts/generate_dataset_v2.py \
  --data_source placeholder \
  --num_episodes 1 --frames_per_episode 3 \
  --output data/raw/v01_placeholder --seed 42
```

### 3️⃣ HoloOcean (2-3min)
```bash
conda activate holoocean
python scripts/generate_dataset_v2.py \
  --data_source holoocean \
  --num_episodes 1 --frames_per_episode 3 \
  --output data/raw/v01_holoocean --seed 42
```

---

## 📁 New Files Created

**Scripts:**
- ✅ `scripts/run_holoocean_smoke_test.py` (131 lines)

**Config:**
- ✅ `configs/scenarios/holoocean_smoke_flatwall.py` (52 lines)

**Docs:**
- ✅ `HOLOOCEAN_INTEGRATION_STATUS.md` (full guide)
- ✅ `WEEK3_STATUS.md` (quick ref)
- ✅ `FINAL_SUMMARY_WEEK3.md` (complete)

---

## ✅ Success Looks Like

**Test 1:** `✓ Smoke test PASSED`  
**Test 2:** `data_source: "placeholder"`  
**Test 3:** `holoocean_integrated: true`

---

## ❌ If Fails

```bash
[command] 2>&1 | tee error.log
```
Paste `error.log` → I'll debug

---

**Start here:** Test 1 ☝️
