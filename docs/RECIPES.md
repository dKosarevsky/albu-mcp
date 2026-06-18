# MCP Host Recipes

These recipes are short host-facing workflows for common AlbumentationsX MCP sessions.

`recommend_recipe` returns structured `explanations` for the selected quality profile, targets, feedback tags, and next
workflow tools. MCP hosts should surface those fields when asking the user to confirm whether a starter workflow matches
the dataset and review goal.

## Classification Robustness

Use profile `classification-robustness`.

1. Call `recommend_recipe` with task `classification` and intensity `medium`.
2. Render a small balanced preview batch.
3. Use `compare_preview_runs` and inspect `quality_summary.findings` plus contact sheets.
4. Ask the user to choose feedback tags such as `too_noisy`, `too_blurry`, or `object_unrecognizable`.
5. When the user points to a concrete preview, call `record_preview_feedback` with the image and variant index.
6. Call `list_preview_feedback` and reuse `aggregated_feedback_tags` for the next adjustment.
7. Render two or three candidates when feedback is ambiguous, then call `rank_preview_candidates`.
8. Call `score_dataset_preview_candidates` to compare metric ranges and finding counts.
9. Persist the accepted or rejected outcome with `record_tuning_decision`.
10. Export a visual handoff with `export_preview_report`; Markdown reports include image refs, HTML reports include
   contact sheet thumbnails, and both include matching concrete feedback.

## Detection Annotation Review

Use profile `detection-annotation-review`.

1. Call `recommend_recipe` with task `object_detection`, targets `["image", "bboxes"]`, and intensity `low`.
2. Render previews with bbox annotations and inspect overlay contact sheets.
3. Use quality profile `detection`.
4. Inspect `quality_summary.annotation_summary` and findings such as `candidate_bbox_loss`.
5. Re-render with the same inputs after every adjustment.
6. Treat `too_distorted` and `object_unrecognizable` as the first feedback tags to consider.
7. Export only after overlays remain aligned and `summarize_tuning_session` reports `export_ready`.

## Segmentation Mask Review

Use profile `segmentation-mask-review`.

1. Call `recommend_recipe` with task `segmentation`, targets `["image", "mask"]`, and intensity `low`.
2. Validate mask-compatible target settings before previewing.
3. Render annotation overlays and compare boundaries between baseline and candidate.
4. Use quality profile `segmentation`.
5. Check `candidate_mask_coverage_drop` before accepting aggressive geometric transforms.
6. Use `too_distorted:high` only when masks are clearly misaligned.
7. Prefer lower geometric intensity until overlays remain stable across examples.

## OCR Document Robustness

Use profile `ocr-document-robustness`.

1. Call `recommend_recipe` with task `ocr` and intensity `low`.
2. Review text legibility before accepting perspective, compression, or blur changes.
3. Use quality profile `ocr`.
4. Use `too_blurry`, `too_distorted`, or `object_unrecognizable:high` when characters become unreadable.
5. Treat high clipping, low entropy, and sharpness-drop findings as reasons to re-render a lighter candidate.
6. Export only after the user accepts contact sheets for the target document style.

## Tuning Decision Journal

After every accepted or rejected candidate:

1. Call `record_preview_feedback` for any concrete examples the user named during visual review.
2. For one-off decisions, call `summarize_tuning_session` and `record_tuning_decision`.
3. For multi-turn review, call `start_tuning_session` once and `record_tuning_session_step` after each candidate.
4. Call `close_tuning_session` when the user accepts a final candidate or rejects the whole attempt.
5. Call `archive_tuning_session` for superseded sessions and `cleanup_tuning_sessions` during long-running host use.
6. Call `list_tuning_sessions` to resume active sessions or inspect accepted, rejected, and archived sessions.
7. Call `list_tuning_decisions` with `ranked=true` when choosing the best candidate across several attempts.
8. Use `accepted_only=true` before final export if the host needs a short list of accepted candidates.
9. Call `export_preview_report` with `output_format="html"` for visual handoff with contact sheet thumbnails and
   matching concrete feedback.
10. Call `export_tuning_session` or `export_tuning_report` with `output_format="markdown"` for handoff or `"json"` for
   automation.

## Resource Discovery

MCP hosts can read:

- `albumentationsx://diagnostics/guide`
- `albumentationsx://workflows/catalog`
- `albumentationsx://workflows/task-profiles`
- `albumentationsx://workflows/preview-tuning`
- `albumentationsx://workflows/annotation-preview`
- `albumentationsx://recipes/catalog`
- `albumentationsx://examples/client-smoke`
- `albumentationsx://examples/first-preview`
- `albumentationsx://examples/diagnostics`
- `albumentationsx://examples/review-loop`
- `albumentationsx://examples/report-handoff`

Use `albumentationsx://examples/client-smoke` immediately after adding the server to a host. It verifies resource
discovery, recipe discovery, `recommend_recipe`, `validate_pipeline`, and `run_host_smoke_check` without reading user
image data. A healthy `run_host_smoke_check` response returns `preview_ready: true` and a `preview_request_template` for
the first small preview. Replace the placeholder image path, call `validate_preview_request`, and only then call
`render_preview_batch`.
Use `albumentationsx://diagnostics/guide` plus `diagnose_environment` when preview setup fails, local paths are rejected,
or host-side tool discovery looks stale.
