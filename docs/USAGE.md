# AlbumentationsX MCP Usage

This server is intended for preview-driven augmentation work with a local MCP host. It exposes AlbumentationsX metadata,
pipeline validation, conservative presets, deterministic previews, and reproducible exports without executing arbitrary
Python code.

## Host Configuration

For copyable host snippets, PyPI install, bounded local access, and troubleshooting, start with
[INSTALL.md](INSTALL.md). This page focuses on the augmentation workflow after the server is connected.
For a copyable host prompt that works across Claude Desktop, Claude Code, Cursor, and Codex, see
[examples/first_preview_workflow.md](../examples/first_preview_workflow.md).
After connecting a new host, read `albumentationsx://examples/client-smoke` for a short smoke playbook before rendering
local previews.
When preview setup is unclear, read `albumentationsx://diagnostics/guide` and call `diagnose_environment` before
changing augmentation pipelines.
For a single read-only preflight, call `run_host_smoke_check` and continue only when `preview_ready` is true. For a
real local dataset folder, read `albumentationsx://examples/dataset-onboarding` and call `plan_dataset_onboarding`
before rendering.

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
2. Call `diagnose_environment` if roots, artifacts, or host discovery are uncertain.
3. Call `validate_pipeline` before rendering or exporting.
4. Call `run_host_smoke_check`; when `preview_ready` is true, replace the placeholder path in
   `preview_request_template.request`.
5. For a real folder, call `plan_dataset_onboarding` with `dataset_path`, task, targets, and a small `max_images`.
6. Call `validate_preview_request` after filling or receiving local image paths and before rendering.
7. Call `explain_pipeline` to identify likely preview risks and feedback tags.
8. Call `render_preview_batch` on a small local image set.
9. Review the generated `contact_sheet` artifact.
10. Use `compare_preview_runs` when comparing a baseline preview to an adjusted candidate preview.
11. Review `suggested_feedback_tags` as candidates, then ask the user which tags match the contact sheets.
12. Call `adjust_pipeline` with tags from `list_feedback_tags`, for example `too_noisy`, `too_noisy:high`, or
   `too_distorted`.
13. Re-render one or more candidates with the same input set.
14. Call `rank_preview_candidates` when multiple candidates need comparison.
15. Call `score_dataset_preview_candidates` to inspect cross-candidate metric ranges and finding counts.
16. Call `record_preview_feedback` when the user points to a concrete image and variant, for example
    "example 8 is too noisy".
17. Call `list_preview_feedback` and reuse `aggregated_feedback_tags` for the next `adjust_pipeline` call.
18. Call `start_tuning_session` when the review will take multiple user feedback turns.
19. Call `record_tuning_session_step` after each baseline-to-candidate comparison.
20. Call `record_tuning_decision` for one-off accepted or rejected candidate decisions.
21. Call `export_preview_report` for a visual Markdown or HTML handoff that includes matching concrete feedback.
22. Call `export_tuning_session` or `export_tuning_report`, then `export_pipeline` once the preview set is acceptable.

## Diagnostics

Use `diagnose_environment` before preview rendering when a host has stale tool discovery, rejected local paths, or missing
artifacts. The response includes `status`, ordered `checks`, check-level `severity`, `warnings`, structured
`remediation_actions`, text `next_actions`, and normalized environment details. The tool does not inspect datasets; with
`include_write_probe=true`, it writes and removes one small probe file under `artifact_root`.

Prefer `remediation_actions` for automation. Stable action codes include `fix_allowed_root`, `fix_artifact_root`,
`fix_artifact_permissions`, `refresh_host_surface`, `reinstall_package`, and `proceed_with_preview_smoke`.

Read `albumentationsx://diagnostics/guide` for the canonical troubleshooting flow and
`albumentationsx://examples/diagnostics` for a host example. Common findings include `allowed_root_missing`,
`artifact_root_write_probe_failed`, and missing public MCP surface entries after a host upgrade.

## Host Smoke

Use `run_host_smoke_check` after connecting a host and before the first local preview. It combines
`diagnose_environment`, `recommend_recipe`, and `validate_pipeline` into one read-only report. When `preview_ready` is
true, copy `preview_request_template.request`, replace the placeholder input path with one small image under an allowed
root, call `validate_preview_request`, then call `render_preview_batch`. When `preview_ready` is false, follow
`remediation_actions` before rendering.

## Dataset Onboarding

Use `plan_dataset_onboarding` when the user points the host at a real local dataset folder and asks for the first safe
preview. The tool is read-only: it checks that `dataset_path` is under an allowed root, scans supported image extensions,
selects a bounded deterministic sample, recommends a recipe, validates the pipeline, and returns a
`preview_request_template`.

Call `validate_preview_request` with `preview_request_template.request` before rendering. Stable remediation action codes
include `move_dataset_under_allowed_root`, `fix_dataset_path`, `add_dataset_images`, and `fix_recommended_pipeline`.

## Preview Request Validation

Use `validate_preview_request` after filling `preview_request_template.request` and before rendering user-provided paths.
The tool is read-only: it validates request schema, pipeline compatibility, input files, mask files, allowed-root
membership, and annotation count without reading image bytes or writing artifacts.

The response includes `status`, `valid`, ordered `checks`, `warnings`, `next_actions`, `remediation_actions`, and
`normalized_request` when schema validation succeeds. Stable check codes include `input_path_missing`,
`input_path_outside_allowed_root`, `mask_path_missing`, `mask_path_outside_allowed_root`, and
`annotation_count_mismatch`.

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

Use `start_tuning_session` when an MCP host is running an interactive loop such as "example 8 is too noisy, try a lighter
candidate". The session stores the task, targets, baseline run id, quality profile, ordered comparison steps, accepted
candidate id, and next actions in `tuning_sessions.json` under the artifact root. After rendering each candidate, call
`record_tuning_session_step` with the baseline id, candidate id, feedback tags, `accepted` state, reviewer notes, and
quality profile. Use `list_tuning_sessions` to resume active or accepted sessions, and `export_tuning_session` to hand off
a compact Markdown or JSON session record. The export also writes a report artifact under
`<artifact-root>/tuning-sessions/` and returns its `artifact://` URI, digest, MIME type, and byte size.

Use `close_tuning_session` when the review ends without another candidate render. Set `status="accepted"` with an
accepted candidate id, or `status="rejected"` when no candidate remains usable. Use `archive_tuning_session` to hide a
completed session from normal review lists without deleting its audit trail. Use `cleanup_tuning_sessions` to prune older
session records; active sessions are protected unless `include_active=true`.

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
paths, Markdown image refs or HTML thumbnails, metric ranges, finding counts, matching tuning decisions, and matching
concrete preview feedback from `record_preview_feedback`. When matching interactive tuning sessions exist, the report
also includes their session timeline, reviewer notes, and links to exported Markdown session artifacts.

## Feedback Severity

`adjust_pipeline` accepts the base tags from `list_feedback_tags` and optional severity suffixes:

- `:low` applies a lighter reduction when only a few examples are slightly too strong.
- `:medium` is the default and matches the base tag behavior.
- `:high` applies a stronger reduction when previews are clearly unusable.

Examples: `too_noisy:low`, `too_blurry:medium`, `too_distorted:high`, and `object_unrecognizable:high`.

`compare_preview_runs` may return `suggested_feedback_tags` based on candidate transform names. Treat them as review
candidates only; they are not an automatic verdict about image quality.

## Concrete Preview Feedback

Use `record_preview_feedback` when the user points to one concrete preview example instead of giving only global
feedback. Indices are zero-based in the tool call and one-based in the returned `review_target`.

```json
{
  "run_id": "candidate-run-id",
  "image_index": 7,
  "variant_index": 0,
  "feedback_tags": ["too_noisy:high"],
  "note": "example 8 is too noisy",
  "accepted": false
}
```

Then call `list_preview_feedback` for the same run and pass `aggregated_feedback_tags` to `adjust_pipeline`. Accepted
example feedback can use `accepted=true` with no tags, but negative feedback must include at least one structured tag.

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

The golden suite includes a real sample first-preview smoke and a preview-request troubleshooting scenario. They call
`run_host_smoke_check`, read `albumentationsx://examples/first-preview`, validate filled preview requests, render
deterministic local sample PNGs, read preview manifests, compare runs with `quality_summary`, and delete generated runs
through MCP stdio.

Public MCP contract changes should also follow [docs/COMPATIBILITY.md](COMPATIBILITY.md) and update the contract snapshot
when tool, resource, prompt, or representative output schemas change:

```bash
uv run python scripts/export_mcp_contract.py --output tests/fixtures/snapshots/mcp_contract.json
uv run python scripts/export_output_contracts.py --output tests/fixtures/snapshots/output_contracts.json
uv run pytest tests/test_mcp_contract_snapshot.py -q
uv run pytest tests/test_output_contract_snapshots.py -q
```

## Resources

- `albumentationsx://transforms/catalog`: all transform metadata from `albu-spec`.
- `albumentationsx://transforms/{name}`: metadata for one transform.
- `albumentationsx://schemas/pipeline`: JSON Schema for pipeline specs.
- `albumentationsx://feedback-tags`: structured feedback tags accepted by `adjust_pipeline`.
- `albumentationsx://quality-profiles`: task-aware quality profiles accepted by comparison and ranking tools.
- `albumentationsx://recipes/catalog`: task-aware recipe catalog for starter workflows.
- `albumentationsx://diagnostics/guide`: setup diagnostics playbook for MCP hosts.
- `albumentationsx://capabilities`: configured roots, preview limits, and exposed tools.
- `albumentationsx://workflows/catalog`: built-in agent workflow guides.
- `albumentationsx://workflows/task-profiles`: task-specific workflow defaults for common CV workflows.
- `albumentationsx://workflows/preview-tuning`: step-by-step preview tuning workflow.
- `albumentationsx://workflows/annotation-preview`: annotation-aware preview workflow.
- `albumentationsx://examples/client-smoke`: post-install host smoke playbook for capabilities, recipes, recommendation,
  and validation.
- `albumentationsx://examples/first-preview`: first local preview playbook with host smoke, request validation, and
  bounded rendering.
- `albumentationsx://examples/distortion-review`: robustness preview loop for rejected noisy or distorted examples.
- `albumentationsx://examples/diagnostics`: troubleshooting playbook for preview setup and local root issues.
- `albumentationsx://examples/review-loop`: concrete example feedback loop for prompts like "example 8 is too noisy".
- `albumentationsx://examples/report-handoff`: visual report handoff loop after ranking and decisions.

## Prompts

- `build_robustness_augmentation_session`: guide preview-driven robustness augmentation work.
- `run_first_preview_review`: guide the first local preview through host smoke and request validation.
- `compare_preview_runs_for_feedback`: compare two preview runs before choosing feedback tags.
- `tune_pipeline_from_preview_feedback`: adjust and re-render from a concrete preview run.
- `export_reproducible_pipeline`: export an accepted run with reproducibility context.
