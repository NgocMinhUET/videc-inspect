# ViDEC-Inspect v0.2 — Physics-Aware Synthesis Status

**Version:** 0.2 (Physics-Aware Procedural Synthesis)
**Scope:** Adds a physics-aware data source on top of the v0.1 scaffold.
**Out of scope:** GAN/diffusion generation, real-data redistribution.

## What is new in v0.2

- `PhysicsAwareFlatWallSource` — concrete-like RGB background (fBm + stain + biofouling), metric depth, and water/lighting metadata.
- `src/synthesis/underwater_optics.py` — channel-wise attenuation + backscatter + turbidity blur + lighting falloff (Jaffe–McGlamery-style).
- `src/synthesis/camera_model.py` — exposure, gain, defocus/motion blur, Gaussian + shot noise, optional JPEG compression.
- `src/synthesis/defect_morphology.py` — interpretable morphology priors from `configs/morphology/*.yaml`.
- `src/synthesis/material_model.py` — fBm-based concrete substrate with stains and optional subtle biofouling.
- `generate_dataset_v2.py --data_source physics` — applies optics + camera degradation **after** defect compositing, preserving masks/depth.
- `scripts/compare_v01_v02.py` — quantitative side-by-side report (image stats, ambiguity, verification, severity).

## Theoretical foundation

See `docs/PHYSICS_AWARE_SYNTHESIS_THEORY.md`, which formalises the benchmark
environment as `z = {z_scene, z_defect, z_material, z_water, z_camera, z_task}`
and the generator `G(z) -> {I_rgb, D, A_det, A_geo, A_met, A_ver, M}`, and
includes the image formation equation, defect morphology priors, material
model, sensor degradation model, verification-aware quality model, the
relationship to real datasets, and the explicit positioning against
GAN/diffusion.

## Compatibility

- `--data_source placeholder` behaves identically to v0.1 (no code path changes).
- `--data_source holoocean` behaves identically to v0.1.
- Verification writer input schema (`image_quality` keys) is unchanged: v0.2 simply fills `sharpness_score`/`contrast_score` from physical metrics instead of constants. New keys (`visibility_score`, `color_cast_strength`) are additive.
- Validator taxonomy is unchanged. `biological_growth` remains canonical; `biofouling` is documented as an alias for compatibility with v0.2 vocabulary.

## Pipeline order (v0.2 physics path)

1. `PhysicsAwareFlatWallSource.capture` → clean concrete RGB + metric depth + sampled optics params.
2. `DefectInjector.composite_defects_on_image` → defects composited on clean RGB.
3. `apply_spall_to_depth_map` + `apply_crack_to_depth_map` → depth modifications.
4. `apply_underwater_optics(rgb_with_defects, depth_with_defects, water_type, lighting_level)` → physics-aware degradation.
5. `apply_camera_model(...)` → sensor degradation + JPEG.
6. All five annotation layers written. Verification layer uses the physically derived `sharpness_score`/`contrast_score`/`visibility_score`/`color_cast_strength`.

## Reproducibility

All randomness is driven by `numpy.random.default_rng(seed)`. Seeds are
deterministic combinations of `--seed`, `episode_id`, `frame_idx`, and
stage-specific offsets (e.g. `+7777` for optics, `+11` after optics for
camera), so two runs with the same flags produce identical output.

## Known limitations (academic honesty)

- The underwater optics model is a simplification of full multi-scattering radiative transfer.
- Morphology priors are based on engineering literature with reasonable lognormal/beta distributions; they are not estimated from a single canonical real dataset.
- The material model is procedural and not photometrically calibrated to any specific concrete grade.
- View-angle depth modeling is mild (no full plane-projective rectification).
- No GAN/diffusion refinement is performed; visual realism is bounded by procedural quality.

## How to run

```bash
python scripts/generate_dataset_v2.py \
    --data_source physics \
    --num_episodes 5 \
    --frames_per_episode 5 \
    --output data/raw/v02_physics_test \
    --seed 42

python scripts/validate_dataset.py --data_dir data/raw/v02_physics_test
python scripts/evaluate_baseline.py --data_dir data/raw/v02_physics_test
python scripts/visualize_sample.py \
    --data_dir data/raw/v02_physics_test \
    --episode_id 0 --frame_id 0 --save

python scripts/compare_v01_v02.py \
    --v01 data/raw/v01_full \
    --v02 data/raw/v02_physics_test \
    --output reports/v01_vs_v02_comparison.json
```

## Acceptance summary

| Criterion (Part 8) | Status |
|---|---|
| Placeholder mode still works | preserved (no path change) |
| HoloOcean mode is not broken | preserved (no path change) |
| Physics mode generates valid dataset | implemented |
| Validation passes with zero errors | expected (schema preserved) |
| Output images visibly differ from v0.1 placeholder | yes (concrete texture + attenuation + backscatter) |
| Metadata contains physical parameters and quality metrics | added to `environment` block |
| Verification ambiguity changes with visibility/quality | sharpness/contrast now physically derived |
| All random behavior is seed-controlled | `np.random.default_rng(seed)` throughout |
| Theory document is academically written and does not overclaim | yes |
| No GAN/diffusion is implemented in this phase | confirmed |
