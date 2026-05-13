# Calibration deltas: v0.2 priors vs empirical (smoke-test corpus)

**Run:** `v0.2/v0.1 self-calibration smoke test`
**Optics corpus:** 25 RGB frames from `data/raw/v02_physics_test` (synthetic v0.2 output).
**Morphology corpus:** 100 crack masks + 100 spall masks from `data/raw/v01_full` (v0.1 procedural masks).
**Pixel-to-meter:** 0.00156 (consistent with v0.1 placeholder: standoff 1.5 m, FOV 90°, 1920 px).
**Note:** This is a *smoke test*, not a real calibration. It exists to verify the framework end-to-end. Real calibration requires real underwater corpora (UIEB / EUVP / Sea-thru / public crack-mask sets), per `docs/CALIBRATION_PROTOCOL.md`.

---

## Optics

| Class | Field | v0.2 prior | Empirical (this run) | Status |
|---|---|---|---|---|
| clear    | `beta_rgb`             | [0.15, 0.08, 0.04] | (NaN) | **fallback_v02** (inversion ill-conditioned on synthetic input) |
| clear    | `backscatter_strength` | [0.02, 0.05]       | [0.388, 0.517] | empirical |
| clear    | `blur_sigma`           | [0.0, 0.6]         | [0.78, 2.24]   | empirical (heuristic proxy) |
| clear    | `contrast_scale`       | [0.85, 1.00]       | [0.024, 0.030] | empirical (observed contrast, not multiplier) |
| moderate | `backscatter_strength` | [0.06, 0.14]       | [0.420, 0.506] | empirical |
| moderate | `blur_sigma`           | [0.6, 1.5]         | [0.46, 2.46]   | empirical (heuristic proxy) |
| turbid   | `backscatter_strength` | [0.15, 0.30]       | [0.353, 0.423] | empirical |
| turbid   | `blur_sigma`           | [1.5, 3.0]         | [1.32, 2.46]   | empirical (heuristic proxy) |

**Interpretation.** The smoke test reveals two expected issues that real-data
calibration will fix:
1. `beta_rgb` is unidentifiable when the input image is already attenuated (B ≈ J). On real underwater photos (UIEB/Sea-thru), B is clearly above J and the inversion succeeds. Until then, the YAML falls back to v0.2 defaults and `_field_source` records this fact.
2. The `contrast_scale` field semantically differs between v0.2 (synthesis multiplier in [0.35, 1.0]) and the calibration (observed image contrast, std ≈ 0.025). On real data this field should be reinterpreted as the *prior on observed contrast in a given water type*, not as a multiplier.

---

## Crack morphology (n = 100 v0.1 procedural masks)

| Distribution | v0.2 prior | Empirical | Comment |
|---|---|---|---|
| length (m): `mean_log_m`, `std_log` | (-1.7, 0.6) → median 0.18 m | **(-1.36, 0.23)** → **median 0.257 m**, p10–p90 = 0.198 – 0.337 m | tighter, slightly longer |
| width (mm): `mean_log_mm`, `std_log` | (0.3, 0.6) → median 1.35 mm | **(1.91, 0.27)** → **median 7.76 mm**, p10–p90 = 4.7 – 8.8 mm | v0.1 procedural cracks are **~5× wider** than the engineering prior — a useful insight for v0.3 |
| max width (mm) | — (not exposed as prior) | median 9.36 mm, p10–p90 = 6.2 – 9.7 mm | informative |
| tortuosity (empirical range) | 1.0–3.5 prior | 0.88 – 1.08 | v0.1 procedural cracks are almost straight |

**Actionable finding.** v0.1's `CrackGenerator` produces cracks that are
visibly thicker than literature norms (which describe hairline → 4 mm
moderate → > 4 mm severe). For v0.3, either (a) thin the procedural cracks
during generation, or (b) re-document the v0.1 cracks as "wide-aperture
test cracks". The calibration framework surfaced this discrepancy quantitatively.

---

## Spall morphology (n = 100 v0.1 procedural masks)

| Distribution | v0.2 prior | Empirical | Comment |
|---|---|---|---|
| area (m²): `mean_log_m2`, `std_log` | (-5.5, 0.7) → median 41 cm² | **(-3.88, 0.55)** → **median 224 cm²**, p10–p90 = 107 – 392 cm² | v0.1 spalls are ~5× the prior median |
| perimeter (m, empirical) | — | median 0.59 m, p10–p90 = 0.41 – 0.78 m | informative |
| eccentricity (empirical range) | — | 0.37 – 0.70 | mildly elongated spalls dominate |
| boundary irregularity (empirical range) | radial_perturb_std prior 0.10 – 0.30 | 0.055 – 0.144 | v0.1 spall boundaries are *more regular* than priors |

**Actionable finding.** v0.1 spalls are larger and more regular than the
moderate-spall engineering prior. Either tighten the procedural area
distribution for v0.3, or document these as deliberately-large stress-test
spalls.

---

## Reproducibility

The exact commands that produced these numbers:

```bash
python scripts/calibrate_priors.py \
    --optics_images_dir data/raw/v02_physics_test \
    --optics_image_glob 'rgb.png' \
    --crack_masks_dir   data/raw/v01_full \
    --crack_glob        'crack_*.png' \
    --spall_masks_dir   data/raw/v01_full \
    --spall_glob        'spall_*.png' \
    --pixel_to_meter    0.00156 \
    --source_description "Smoke test v2: v0.2 synthetic + v0.1 masks, DCP B_c" \
    --reports_dir       reports/calibration
```

Produced:
- `configs/synthesis/underwater_optics.calibrated.yaml`
- `configs/morphology/crack_model.calibrated.yaml`
- `configs/morphology/spall_model.calibrated.yaml`
- `reports/calibration/optics_provenance.json`
- `reports/calibration/morphology_provenance.json`
- `reports/calibration/calibration_summary.json`
- this document.
