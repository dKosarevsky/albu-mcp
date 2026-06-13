# AlbumentationsX MCP Usage

This server is intended for preview-driven augmentation work with a local MCP host. It exposes AlbumentationsX metadata,
pipeline validation, conservative presets, deterministic previews, and reproducible exports without executing arbitrary
Python code.

## Host Configuration

Use `examples/claude_desktop_config.json` as a starting point and replace `/path/to/albu-mcp` with the repository path:

```json
{
  "mcpServers": {
    "albumentationsx": {
      "command": "uv",
      "args": ["run", "albumentationsx-mcp"],
      "cwd": "/path/to/albu-mcp"
    }
  }
}
```

For preview rendering, constrain filesystem access explicitly:

```bash
uv run albumentationsx-mcp \
  --allowed-root /path/to/images \
  --artifact-root /path/to/albu-mcp/artifacts
```

By default, the artifact index keeps the latest 100 preview runs. Set `ALBU_MCP_MAX_PREVIEW_RUNS` to change that
retention limit for long-running MCP hosts.

## Agent Workflow

1. Call `recommend_recipe` for the target task, intensity, quality profile, feedback tags, explanations, and next tools.
2. Call `validate_pipeline` before rendering or exporting.
3. Call `explain_pipeline` to identify likely preview risks and feedback tags.
4. Call `render_preview_batch` on a small local image set.
5. Review the generated `contact_sheet` artifact.
6. Use `compare_preview_runs` when comparing a baseline preview to an adjusted candidate preview.
7. Review `suggested_feedback_tags` as candidates, then ask the user which tags match the contact sheets.
8. Call `adjust_pipeline` with tags from `list_feedback_tags`, for example `too_noisy`, `too_noisy:high`, or
   `too_distorted`.
9. Re-render one or more candidates with the same input set.
10. Call `rank_preview_candidates` when multiple candidates need comparison.
11. Call `score_dataset_preview_candidates` to inspect cross-candidate metric ranges and finding counts.
12. Call `summarize_tuning_session` to inspect `quality_score`, `quality_risk`, and `export_ready`.
13. Call `record_tuning_decision` to persist the accepted or rejected candidate.
14. Call `export_preview_report` for a visual Markdown or HTML handoff.
15. Call `export_tuning_report` for a decision journal handoff, then `export_pipeline` once the preview set is acceptable.

## Preview Artifacts

Each preview run writes:

- one PNG per input and variant
- `contact_sheet.png` for quick review
- optional overlay PNGs when bboxes, keypoints, or masks are supplied
- optional `overlay_contact_sheet.png` for annotation-aware review
- `manifest.json` with input paths, pipeline JSON, artifact hashes, and timestamps
- `summary` inside `manifest.json` with input counts, seeds, transform names, artifact counts, contact sheets, and warnings
- `annotation_observations` when bboxes, keypoints, or masks are supplied

Use `list_preview_runs` to find recent runs, `get_preview_manifest` to retrieve a manifest by run id,
`compare_preview_runs` to compare two manifests, `delete_preview_run` to remove one run, and `cleanup_preview_runs` to
prune older runs.

For multi-image review, call `render_preview_batch` with the same request schema as `render_preview`. It writes per-image
variants plus a shared contact sheet for quick side-by-side review.

`compare_preview_runs` includes `quality_summary` when preview image artifacts are still available locally. It reports
brightness, contrast, sharpness, saturation, colorfulness, entropy, clipping, candidate-minus-baseline deltas, and
structured `findings`. Missing or unreadable local artifacts are reported as `quality_warnings` instead of failing the
comparison.

Use `list_quality_profiles` before comparing task-specific previews. The built-in profiles are `balanced`,
`classification`, `detection`, `segmentation`, and `ocr`. Pass `quality_profile` to `compare_preview_runs`,
`summarize_tuning_session`, `record_tuning_decision`, or `rank_preview_candidates` when a task needs stricter findings,
for example OCR sharpness and entropy or detection bbox retention.

When preview manifests include `annotation_observations`, `quality_summary.annotation_summary` reports bbox, keypoint,
and mask retention aggregates plus deltas. Findings such as `candidate_bbox_loss`, `candidate_keypoint_loss`, and
`candidate_mask_coverage_drop` are review prompts for the host, not automatic rejection rules.

Call `summarize_tuning_session` after comparing a baseline and candidate. It combines feedback tags, suggested tags,
quality deltas, `quality_score`, `quality_risk`, structured `quality_findings`, and an `export_ready` flag so the host
can decide whether to ask for more feedback or call `export_pipeline`.

Use `record_tuning_decision` after the user accepts or rejects a candidate. Decisions are stored in
`tuning_decisions.json` under the configured artifact root. `list_tuning_decisions` can return newest-first history or
score-ranked candidates with `ranked=true`, and can restrict output to accepted decisions with `accepted_only=true`.
Use `export_tuning_report` to render the same journal as Markdown for humans or JSON for automation.

`rank_preview_candidates` accepts one baseline id and several candidate ids:

```json
{
  "baseline_run_id": "baseline-run-id",
  "candidate_run_ids": ["candidate-a", "candidate-b"],
  "feedback_tags_by_candidate": {
    "candidate-a": ["too_noisy:low"],
    "candidate-b": ["too_blurry"]
  },
  "accepted_candidate_ids": ["candidate-a"],
  "quality_profile": "ocr"
}
```

Ranking is deterministic: higher `quality_score`, lower `quality_risk`, export-ready candidates, then candidate run id.

`score_dataset_preview_candidates` accepts the same run ids and returns dataset-level metric stats plus finding counts:

```json
{
  "baseline_run_id": "baseline-run-id",
  "candidate_run_ids": ["candidate-a", "candidate-b"],
  "quality_profile": "detection"
}
```

Use `export_preview_report` after scoring or recording a decision. It writes a Markdown or HTML report under
`artifact_root/reports/` and returns a `report` artifact with the rendered content, ranked candidates, contact sheet
paths, Markdown image refs or HTML thumbnails, metric ranges, finding counts, and matching tuning decisions.

## Feedback Severity

`adjust_pipeline` accepts the base tags from `list_feedback_tags` and optional severity suffixes:

- `:low` applies a lighter reduction when only a few examples are slightly too strong.
- `:medium` is the default and matches the base tag behavior.
- `:high` applies a stronger reduction when previews are clearly unusable.

Examples: `too_noisy:low`, `too_blurry:medium`, `too_distorted:high`, and `object_unrecognizable:high`.

`compare_preview_runs` may return `suggested_feedback_tags` based on candidate transform names. Treat them as review
candidates only; they are not an automatic verdict about image quality.

## Annotation Previews

`render_preview` accepts an optional `annotations` list with one item per `input_paths` entry:

```json
{
  "request": {
    "input_paths": ["/path/to/images/example.png"],
    "annotations": [
      {
        "bboxes": [[4, 5, 20, 24]],
        "bbox_labels": ["object"],
        "keypoints": [[12, 14]],
        "mask_path": "/path/to/images/example-mask.png"
      }
    ],
    "pipeline": {
      "transforms": [{"name": "HorizontalFlip", "p": 1.0}],
      "bbox_params": {"format": "pascal_voc", "label_fields": ["labels"]},
      "keypoint_params": {"format": "xy", "remove_invisible": false}
    },
    "variants_per_image": 2
  }
}
```

Mask paths are resolved through the same `--allowed-root` policy as input images.

Preview manifests record annotation observations like this:

```json
{
  "annotation_observations": [
    {
      "image_index": 0,
      "variant_index": 0,
      "input_bbox_count": 1,
      "output_bbox_count": 1,
      "input_keypoint_count": 1,
      "output_keypoint_count": 1,
      "input_mask_coverage": 0.25,
      "output_mask_coverage": 0.25
    }
  ]
}
```

## Golden Evals

Run executable MCP scenarios locally before changing tool contracts:

```bash
uv run python scripts/run_golden_evals.py
```

## Resources

- `albumentationsx://transforms/catalog`: all transform metadata from `albu-spec`.
- `albumentationsx://transforms/{name}`: metadata for one transform.
- `albumentationsx://schemas/pipeline`: JSON Schema for pipeline specs.
- `albumentationsx://feedback-tags`: structured feedback tags accepted by `adjust_pipeline`.
- `albumentationsx://quality-profiles`: task-aware quality profiles accepted by comparison and ranking tools.
- `albumentationsx://recipes/catalog`: task-aware recipe catalog for starter workflows.
- `albumentationsx://capabilities`: configured roots, preview limits, and exposed tools.
- `albumentationsx://workflows/catalog`: built-in agent workflow guides.
- `albumentationsx://workflows/task-profiles`: task-specific workflow defaults for common CV workflows.
- `albumentationsx://workflows/preview-tuning`: step-by-step preview tuning workflow.
- `albumentationsx://workflows/annotation-preview`: annotation-aware preview workflow.

## Prompts

- `build_robustness_augmentation_session`: guide preview-driven robustness augmentation work.
- `compare_preview_runs_for_feedback`: compare two preview runs before choosing feedback tags.
- `tune_pipeline_from_preview_feedback`: adjust and re-render from a concrete preview run.
- `export_reproducible_pipeline`: export an accepted run with reproducibility context.
