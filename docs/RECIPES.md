# MCP Host Recipes

These recipes are short host-facing workflows for common AlbumentationsX MCP sessions.

## Classification Robustness

Use profile `classification-robustness`.

1. Call `recommend_pipeline` with task `classification`, targets `["image"]`, and intensity `medium`.
2. Render a small balanced preview batch.
3. Use `compare_preview_runs` and inspect `quality_summary.findings` plus contact sheets.
4. Ask the user to choose feedback tags such as `too_noisy`, `too_blurry`, or `object_unrecognizable`.
5. Call `summarize_tuning_session` and check `quality_score`, `quality_risk`, and `export_ready`.
6. Persist the accepted or rejected outcome with `record_tuning_decision`.

## Detection Annotation Review

Use profile `detection-annotation-review`.

1. Call `recommend_pipeline` with task `object_detection`, targets `["image", "bboxes"]`, and intensity `low`.
2. Render previews with bbox annotations and inspect overlay contact sheets.
3. Inspect `quality_summary.annotation_summary` and findings such as `candidate_bbox_loss`.
4. Re-render with the same inputs after every adjustment.
5. Treat `too_distorted` and `object_unrecognizable` as the first feedback tags to consider.
6. Export only after overlays remain aligned and `summarize_tuning_session` reports `export_ready`.

## Segmentation Mask Review

Use profile `segmentation-mask-review`.

1. Validate mask-compatible target settings before previewing.
2. Render annotation overlays and compare boundaries between baseline and candidate.
3. Check `candidate_mask_coverage_drop` before accepting aggressive geometric transforms.
4. Use `too_distorted:high` only when masks are clearly misaligned.
5. Prefer lower geometric intensity until overlays remain stable across examples.

## OCR Document Robustness

Use profile `ocr-document-robustness`.

1. Start with low intensity document transforms.
2. Review text legibility before accepting perspective, compression, or blur changes.
3. Use `too_blurry`, `too_distorted`, or `object_unrecognizable:high` when characters become unreadable.
4. Treat high clipping, low entropy, and sharpness-drop findings as reasons to re-render a lighter candidate.
5. Export only after the user accepts contact sheets for the target document style.

## Tuning Decision Journal

After every accepted or rejected candidate:

1. Call `summarize_tuning_session` with the chosen feedback tags and acceptance state.
2. Call `record_tuning_decision` with the same run ids and user-facing notes.
3. Call `list_tuning_decisions` with `ranked=true` when choosing the best candidate across several attempts.
4. Use `accepted_only=true` before final export if the host needs a short list of accepted candidates.

## Resource Discovery

MCP hosts can read:

- `albumentationsx://workflows/catalog`
- `albumentationsx://workflows/task-profiles`
- `albumentationsx://workflows/preview-tuning`
- `albumentationsx://workflows/annotation-preview`
