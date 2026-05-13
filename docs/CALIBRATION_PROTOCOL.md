# ViDEC-Inspect — Empirical Prior Calibration Protocol

**Version:** 0.2.1 (calibration addendum to v0.2)
**Scope:** Defines how the v0.2 priors in `configs/synthesis/*.yaml` and
`configs/morphology/*.yaml` are empirically calibrated against real
underwater images and real defect masks, and how to reproduce the calibration.
Outputs are sibling `*.calibrated.yaml` files plus a provenance JSON; the
v0.2 defaults remain in place so the original engineering priors are always
recoverable.

This protocol is the **single point of contact** between ViDEC-Inspect and
real datasets. No real-data redistribution happens; only distributional
statistics are extracted and stored in YAML.

---

## 1. What this protocol calibrates

| Subject | Source data needed | Output YAML | Provenance JSON |
|---|---|---|---|
| Underwater optics (`beta_rgb`, backscatter, blur, contrast) | RGB underwater photos | `configs/synthesis/underwater_optics.calibrated.yaml` | `reports/calibration/optics_provenance.json` |
| Crack morphology (length, width, tortuosity) | Binary crack masks + pixel-to-meter | `configs/morphology/crack_model.calibrated.yaml` | `reports/calibration/morphology_provenance.json` |
| Spall morphology (area, perimeter, eccentricity, irregularity) | Binary spall masks + pixel-to-meter | `configs/morphology/spall_model.calibrated.yaml` | same as above |
| Material (dry/wet concrete reflectance, roughness) | Concrete patches (optional) | (planned) `configs/synthesis/material_model.calibrated.yaml` | `reports/calibration/material_provenance.json` |

Every calibrated YAML is annotated with a `calibration_provenance:` block and
a per-field `_field_source: {empirical, fallback_v02}` map, so any downstream
reader can audit which priors were measured versus which inherited from v0.2.

---

## 2. Method

### 2.1 Optics (no depth required)

Per image, compute:

- channel means \(\mu_R, \mu_G, \mu_B\) and stds \(\sigma_R, \sigma_G, \sigma_B\);
- gray std and Laplacian variance (sharpness proxy);
- color cast magnitude \(\lVert\bar c - \overline{\bar c}\,\mathbf{1}\rVert / \sqrt{3}\);
- veiling/backscatter color \(B\) via the **dark-channel prior** (He et al. 2010):
  1. Per-pixel dark channel \(D(x) = \min_c I_c(x)\), eroded with a 7×7 kernel.
  2. Top 0.1% brightest pixels of \(D\) form the candidate set.
  3. Among candidates, the pixel with highest intensity is \(B\).

Channel-wise attenuation \(\beta_c\) is then estimated under two assumptions
that must be documented in the provenance:

- A representative range \(\bar d\) (default `--d_bar_m 2.0`).
- A neutral reference reflectance \(J\) (default `--reference_J 0.5 0.5 0.5`, grey concrete).

If \(B_c > J_c\) and \(B_c > \mu_c\), then
\(t_c = (B_c - \mu_c) / (B_c - J_c) \in (0,1)\) and \(\beta_c = -\ln(t_c) / \bar d\).
When the inversion is ill-conditioned (typical for synthetic self-calibration
or for images photographed against a brighter-than-reference background), the
estimator returns `NaN` for that image's \(\beta_c\) and the field is filled
with the v0.2 fallback in the calibrated YAML; the `_field_source` flag is
set to `fallback_v02`.

Per-corpus aggregation: median over images for the point estimate; 10th–90th
percentiles for the bracketed prior. If `--labels_csv` is not supplied, the
images are auto-binned into `clear/moderate/turbid` using a turbidity score
\(\tau = 0.5(1 - \text{normContrast}) + 0.5\,\text{normColorCast}\), split at
33rd/66th percentiles.

### 2.2 Morphology (from binary masks)

Each binary mask is post-processed with skimage / OpenCV:

**Crack** (skeletonized):
- `length_m` = skeleton pixel count × pixel_to_meter.
- `mean_width_mm` = mask area / skeleton length × pixel_to_meter × 1000.
- `max_width_mm` = max distance-transform value × 2 × pixel_to_meter × 1000.
- `tortuosity` = skeleton length / chord length.
- `orientation_deg` = PCA principal axis of skeleton points.

**Spall** (contour analysis):
- `area_m2` = mask area × pixel_to_meter².
- `perimeter_m` = contour arc length × pixel_to_meter.
- `eccentricity` = √(1 − b²/a²) from fitted ellipse axes.
- `boundary_irregularity` = std/mean of polar radii from centroid.

Lognormal MLE is fit on `length`, `width`, `area`, `perimeter` using
`scipy.stats.lognorm.fit(values, floc=0)`. The resulting `(mean_log, std_log,
clip_{1%,99%})` triple is written directly into the calibrated YAML in the
same schema as v0.2 priors so the synthesis modules consume the calibrated
YAML transparently.

### 2.3 Material (optional)

Per concrete patch image, compute base luminance, micro-roughness (Laplacian
variance), color bias, and high-saturation fraction (stain proxy). Aggregate
to 10th–90th percentile ranges. This module is implemented in
`src/calibration/material_calibration.py` but is not yet wired into the
orchestrator pending a curated concrete-patch corpus.

---

## 3. Reproducing the calibration

### 3.1 Smoke test (no real data required)

To verify the framework end-to-end against the v0.2 synthetic output (optics)
and the v0.1 procedural masks (morphology):

```bash
python scripts/calibrate_priors.py \
    --optics_images_dir data/raw/v02_physics_test \
    --optics_image_glob 'rgb.png' \
    --crack_masks_dir   data/raw/v01_full \
    --crack_glob        'crack_*.png' \
    --spall_masks_dir   data/raw/v01_full \
    --spall_glob        'spall_*.png' \
    --pixel_to_meter    0.00156 \
    --source_description "v0.2/v0.1 self-calibration smoke test" \
    --reports_dir       reports/calibration
```

Expected behavior:
- Optics: `backscatter_strength`, `blur_sigma`, `contrast_scale` become **empirical** in `configs/synthesis/underwater_optics.calibrated.yaml`; `beta_rgb` falls back to v0.2 defaults (because the inversion is ill-conditioned on already-attenuated synthetic data). Both outcomes are recorded in `_field_source`.
- Crack/Spall: lognormal parameters are empirical from the 100 masks per class.

### 3.2 Real calibration (recommended next step for the paper)

When real corpora are available, run the same orchestrator with different
inputs. Examples of recommended corpora:

| Subject | Corpus | Notes |
|---|---|---|
| Optics | **UIEB** (~890 raw underwater images) | Good coverage of clear→turbid water types. |
| Optics | **EUVP** (~12,000 underwater images) | Larger scale, more diversity. |
| Optics | **Sea-thru** (~1,100 images with depth) | If you can use depth, prefer this for `beta_rgb`. |
| Crack masks | Concrete-crack open datasets (e.g., SDNET2018-derived crack masks, or any annotated concrete crack repository) | Need binary masks, not just bounding boxes. |
| Spall masks | Any spall-segmented dataset (ConCrack, ConcreteSpall-derived) | Binary masks. |
| Concrete patches | UDD/Sea-thru cropped concrete regions, or a small in-house set | Helps calibrate substrate appearance. |

Once you have any of these on disk, run:

```bash
python scripts/calibrate_priors.py \
    --optics_images_dir /data/real/uieb/raw \
    --optics_image_glob '*.png' \
    --crack_masks_dir   /data/real/cracks_masks \
    --spall_masks_dir   /data/real/spalls_masks \
    --pixel_to_meter    <YOUR_VALUE> \
    --d_bar_m           2.0 \
    --reference_J       0.5 0.5 0.5 \
    --source_description "UIEB (n=890) + concrete crack masks" \
    --reports_dir       reports/calibration
```

The output YAMLs become the new priors. To switch the synthesis pipeline to
the calibrated priors, replace `configs/synthesis/underwater_optics.yaml` and
the two morphology YAMLs with their `.calibrated.yaml` counterparts (rename),
or update the loaders in `src/synthesis/*` to read the calibrated files
explicitly.

### 3.3 Sea-thru style depth-aware calibration (optional)

For datasets that ship metric depth alongside RGB (e.g., Sea-thru), a much
stronger `beta_c` estimate is achievable: fit per-pixel
\(\log(B_c - I_c(x)) = \log(B_c - J_c) - \beta_c d(x)\) via least squares,
which removes the need for the `--d_bar_m` assumption. This is on the
roadmap as `src/calibration/optics_calibration_seathru.py` and is not yet
wired into the orchestrator.

---

## 4. Provenance and auditability

Every calibration run produces:

- `reports/calibration/calibration_summary.json` — top-level summary.
- `reports/calibration/optics_provenance.json` — per-image stats and the aggregated priors.
- `reports/calibration/morphology_provenance.json` — full lognormal fits with `(n, median, p10, p90)` per distribution.
- `_field_source` map embedded in each calibrated YAML so the *source of truth*
  for every prior is one map lookup away.

Best practice for paper submissions:

1. Commit the calibration provenance JSONs to the repo.
2. Reference the calibration corpus in the paper's data section.
3. Quote the empirical median + p10/p90 ranges for the key priors; cite the
   YAML by hash.

---

## 5. Limitations (academic honesty)

- **Optics without depth**: `beta_c` is identifiable only up to the assumed `d_bar`. The output is therefore a *prior range*, not a measurement. Use Sea-thru-style depth-aware calibration when possible (Section 3.3).
- **Reference reflectance**: `J = 0.5` grey is a placeholder. A measured dry-concrete reflectance per inspection target site is more rigorous.
- **Auto-binning**: when water-type labels are unavailable, the auto-binner uses contrast + color cast quantiles. Human-labelled water types should be supplied via `--labels_csv` for paper-grade rigor.
- **Morphology priors require masks**: bounding boxes alone are not sufficient. Width and area distributions need pixel-accurate segmentation.
- **Material model**: implemented but not wired into the orchestrator; planned for v0.2.2.
