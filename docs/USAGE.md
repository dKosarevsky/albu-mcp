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
2. Call `plan_augmentation_policy` when the user asks for a task/objective policy rather than a generic recipe.
3. Call `plan_policy_iteration` when concrete candidate feedback should drive the next preview-gated policy loop.
4. Call `diagnose_environment` if roots, artifacts, or host discovery are uncertain.
5. Call `validate_pipeline` before rendering or exporting.
6. Call `run_host_smoke_check`; when `preview_ready` is true, replace the placeholder path in
   `preview_request_template.request`.
7. For a real folder, call `plan_dataset_onboarding` with `dataset_path`, task, targets, and a small `max_images`.
8. Call `validate_preview_request` after filling or receiving local image paths and before rendering.
9. Call `explain_pipeline` to identify likely preview risks and feedback tags.
10. Call `render_preview_batch` on a small local image set.
11. Review the generated `contact_sheet` artifact.
12. Use `compare_preview_runs` when comparing a baseline preview to an adjusted candidate preview.
13. Review `suggested_feedback_tags` as candidates, then ask the user which tags match the contact sheets.
14. Call `adjust_pipeline` with tags from `list_feedback_tags`, for example `too_noisy`, `too_noisy:high`, or
   `too_distorted`.
15. Re-render one or more candidates with the same input set.
16. Call `rank_preview_candidates` when multiple candidates need comparison.
17. Call `score_dataset_preview_candidates` to inspect cross-candidate metric ranges and finding counts.
18. Call `record_preview_feedback` when the user points to a concrete image and variant, for example
    "example 8 is too noisy".
19. Call `list_preview_feedback` and reuse `aggregated_feedback_tags` for the next `adjust_pipeline` call.
20. Call `start_tuning_session` when the review will take multiple user feedback turns.
21. Call `record_tuning_session_step` after each baseline-to-candidate comparison.
22. Call `record_tuning_decision` for one-off accepted or rejected candidate decisions.
23. Call `export_preview_report` for a visual Markdown or HTML handoff that includes matching concrete feedback.
24. Call `export_tuning_session` or `export_tuning_report`, then `export_pipeline` once the preview set is acceptable.

## Operator CLI

Use the package CLI for release evidence and beta records without importing repository-only scripts:

```bash
albu-mcp host setup-probe --host Codex --live --format json
albu-mcp preview first-pack --dataset-path /absolute/path/to/images --allowed-root /absolute/path/to --artifact-root /absolute/path/to/albu-artifacts --format json
albu-mcp intake bundle --output-dir docs/intake-bundle --format markdown
albu-mcp activation command-center --format markdown
albu-mcp activation runbook --format markdown
albu-mcp activation proof-sprint --output-dir docs/proof-sprint --format markdown
albu-mcp activation execution-workspace --output-dir docs/proof-execution --format markdown
albu-mcp activation real-proof-run --output-dir docs/real-proof-run-1 --format markdown
albu-mcp activation evidence-first-cycle --host Codex --output-dir docs/evidence-first-cycle --format markdown
albu-mcp activation acquisition-cycle --host Codex --output-dir docs/acquisition-cycle --format markdown
albu-mcp activation evidence-cockpit --host Codex --output-dir docs/evidence-cockpit --format markdown
albu-mcp activation evidence-product-loop --host Codex --output-dir docs/evidence-product-loop --format markdown
albu-mcp activation real-adoption-cycle --host Codex --output-dir docs/real-adoption-cycle --format markdown
albu-mcp activation first-product-fix --host Codex --format json
albu-mcp activation first-product-fix --host Codex --output-dir docs/first-product-fix --format markdown
albu-mcp activation product-fix-implementation-plan --host Codex --format json
albu-mcp activation product-fix-implementation-plan --host Codex --output-dir docs/product-fix-implementation-plan --format markdown
albu-mcp activation product-fix-execution-guard --host Codex --format json
albu-mcp activation product-fix-execution-guard --host Codex --output-dir docs/product-fix-execution-guard --format markdown
albu-mcp activation product-fix-validation --host Codex --format json
albu-mcp activation product-fix-validation --host Codex --output-dir docs/product-fix-validation --format markdown
albu-mcp activation product-fix-outcome-capture --host Codex --output-dir docs/product-fix-outcome-capture --format markdown
albu-mcp activation product-fix-outcome --host Codex --format json
albu-mcp activation product-fix-outcome --host Codex --output-dir docs/product-fix-outcome --format markdown
albu-mcp evidence collect --host Codex --date YYYY-MM-DD --reviewer "Release operator" --format json
albu-mcp evidence run-session --host Codex --format json
albu-mcp evidence execution-packet --host Codex --format json
albu-mcp evidence operator-packet --host Codex --output-dir docs/operator-packets --format markdown
albu-mcp evidence packet-bundle --output-dir docs/operator-packets --format markdown
albu-mcp evidence replay-fixture-pack --output-dir docs/operator-packets --format markdown
albu-mcp evidence session-folder --host Codex --date YYYY-MM-DD --reviewer "Release operator" --output-dir docs/operator-packets --format markdown
albu-mcp evidence session-manifest --host Codex --date 2026-07-01 --reviewer "Release operator" --output-dir docs/operator-packets --format json
albu-mcp evidence validate-manifest --input docs/operator-packets/codex-evidence-session-manifest.json --format json
albu-mcp evidence proof-runner --input docs/operator-packets/codex-evidence-session-manifest.json --format json
albu-mcp evidence import-manifest --input docs/operator-packets/codex-evidence-session-manifest.json --format json
albu-mcp evidence import-wizard --host-manifest docs/operator-packets/codex-evidence-session-manifest.json --host-manifest docs/operator-packets/claude-code-evidence-session-manifest.json --beta-dir docs/beta-response-templates --format json
albu-mcp evidence close-host --host Codex --format json
albu-mcp evidence proof-status --format json
albu-mcp evidence transition-pack --before-host-records docs/HOST_MANUAL_RUNS.json --after-host-records docs/HOST_MANUAL_RUNS.json --beta-records docs/BETA_VALIDATION_RECORDS.json --output-dir docs/operator-packets --format markdown
albu-mcp evidence rc-unblock-preview --format json
albu-mcp evidence transcript-template --host Codex --output-dir docs/operator-packets --format markdown
albu-mcp evidence import-checklist --host Codex --format markdown
albu-mcp evidence validate-import --host Codex --status passed --date 2026-06-30 --evidence "reviewer observed real host UI" --artifact docs/assets/demo/demo_report.md --confirm-real-host-observed --format json
albu-mcp evidence import-artifacts --host Codex --status passed --date 2026-06-30 --evidence "reviewer observed real host UI" --artifact docs/assets/demo/demo_report.md --confirm-real-host-observed
albu-mcp evidence privacy-doctor --format json
albu-mcp evidence artifact-doctor --format json
albu-mcp evidence unblock-plan --format json
albu-mcp evidence doctor --format json
albu-mcp evidence record-host-ui --host Codex --status passed --date 2026-06-28 --evidence "..."
albu-mcp evidence record-first-10-minutes --host Codex --status passed --date 2026-06-28 --evidence "..." --artifact docs/assets/demo/demo_report.md
albu-mcp evidence status
albu-mcp beta campaign-plan --format json
albu-mcp beta loop-pack --output-dir docs/beta-loop --format markdown
albu-mcp beta trial-pack --workflow-id noisy_preview_tuning --participant-role "ML practitioner" --format json
albu-mcp beta intake-wizard --workflow-id noisy_preview_tuning --participant-role "ML practitioner" --format json
albu-mcp beta response-template --output-dir docs/beta-response-templates --format json
albu-mcp beta response-validate --input beta-response.json --format json
albu-mcp beta response-import --input beta-response.json
albu-mcp beta response-import-dir --input-dir docs/beta-response-templates --format json
albu-mcp beta record-attempt --workflow-id noisy_preview_tuning --status needs_followup --attempt-date 2026-06-28 --participant-role "ML practitioner" --summary "..." --triage-bucket review_agent_v3_gap
albu-mcp beta triage --format json
albu-mcp beta report --format json
albu-mcp rc reopen --format json
albu-mcp rc rehearse --format json
albu-mcp rc candidate-packet --format markdown
albu-mcp rc release-owner-packet --format markdown
albu-mcp rc review-pack --output-dir docs/release-owner-review --format markdown
albu-mcp rc go-check --format markdown
albu-mcp distribution readiness --format json
albu-mcp trust audit --format json
albu-mcp trust next --format json
albu-mcp trust dashboard --format markdown
albu-mcp trust gate-transition --before-host-records docs/HOST_MANUAL_RUNS.json --before-beta-records docs/BETA_VALIDATION_RECORDS.json --after-host-records docs/HOST_MANUAL_RUNS.json --after-beta-records docs/BETA_VALIDATION_RECORDS.json --format markdown
```

These commands write privacy-safe JSON records only for explicit `record-*`, `response-import`, `response-import-dir`,
`import-manifest`, `import-wizard --import-ready`, or `import-artifacts` actions. `intake bundle`,
`activation command-center`, `activation runbook`, `activation proof-sprint`, `activation execution-workspace`,
`activation real-proof-run`,
`activation evidence-first-cycle`, `activation acquisition-cycle`, `activation evidence-cockpit`,
`activation evidence-product-loop`, `activation real-adoption-cycle`, `activation first-product-fix`,
`activation product-fix-implementation-plan`, `activation product-fix-execution-guard`, `run-session`,
`activation product-fix-validation`, `activation product-fix-outcome-capture`, `activation product-fix-outcome`,
`host setup-probe`,
`preview first-pack`, `evidence collect`, `execution-packet`, `operator-packet`, `packet-bundle`,
`replay-fixture-pack`, `session-folder`, `session-manifest`, `validate-manifest`, `proof-runner`, `import-wizard`
without `--import-ready`, `close-host`, `proof-status`, `transition-pack`, `rc-unblock-preview`,
`transcript-template`, `import-checklist`, `validate-import`, `privacy-doctor`, `artifact-doctor`, `unblock-plan`,
`doctor`, `campaign-plan`, `loop-pack`, `trial-pack`, `intake-wizard`, `response-template`, `response-validate`,
`rc reopen`, `rc rehearse`,
`rc candidate-packet`, `rc release-owner-packet`, `rc review-pack`, `rc go-check`, `distribution readiness`,
`trust audit`, `trust next`, `trust dashboard`, and `trust gate-transition` are report-only or artifact-only helpers.
`validate-import` and `validate-manifest` check the same fields before recording, and `import-artifacts` requires
`--confirm-real-host-observed` before recording `passed`, so P0 evidence still depends on an actual MCP host UI session
observed by a reviewer. Release and distribution commands are report-only: they print publish commands only when gates
are open and never create tags, releases, or uploads.

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

The response also includes `dataset_structure` when the folder is accessible. This best-effort profile detects common
class-directory layouts, `train`/`val`/`valid`/`validation`/`test` split folders, YOLO `labels/**/*.txt` files, and COCO
JSON manifests with `images`, `annotations`, and `categories`. Hosts can use `detected_layouts`, `class_directories`,
`splits`, `annotation_formats`, `balance_warnings`, and `recipe_hints` to ask better follow-up questions before rendering.
Profiling is advisory: malformed or unsupported annotation files do not block first-preview planning.

For detection datasets, the returned `preview_request_template.request` includes bounded bbox `annotations` when sampled
images can be matched to COCO or YOLO labels. Those annotations are converted to `pascal_voc` bboxes so
`render_preview_batch` can produce `overlay_contact_sheet.png` for the first visual review. If some sampled images do not
have matching labels, the template still preserves `annotations` length and adds a warning to `instructions`.

For segmentation datasets, COCO polygon/RLE masks and YOLO-seg polygons are converted into mask annotations. The
template keeps mask-only payloads for `["image", "mask"]` targets, so preview rendering can produce mask overlays
without sending bboxes to pipelines that do not declare `bbox_params`. The template also includes
`annotation_summary` with matched sample counts, bbox/keypoint counts, mask format counts, and annotation warnings.

Call `validate_preview_request` with `preview_request_template.request` before rendering. Stable remediation action codes
include `move_dataset_under_allowed_root`, `fix_dataset_path`, `add_dataset_images`, and `fix_recommended_pipeline`.

## Dataset Quality Inspection

Use `inspect_dataset_quality` before the first real preview when the host needs a cheap read-only signal about the input
folder. It samples supported images under `--allowed-root`, reports aggregate brightness, contrast, entropy, clipping,
and unreadable files, then recommends whether to continue with `build_review_packet` or repair the dataset first:

```json
{
  "dataset_path": "/absolute/path/to/images",
  "max_images": 8
}
```

The tool does not render augmented variants or mutate files. Treat `findings` as preflight hints; the final review still
comes from `render_preview_batch`, contact sheets, `compare_preview_runs`, and human feedback.

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

Use `plan_preview_review` when the host needs one action-oriented review handoff. It compares baseline and candidate
runs, wraps the tuning summary, returns a review checklist, reports blockers such as changed inputs, and recommends the
next tool: `list_feedback_tags`, `adjust_pipeline`, `render_preview_batch`, or `record_tuning_decision`.

Use `interpret_preview_feedback` before `plan_preview_review` when the user gives free-form comments such as "example 8
is too noisy" or "that set looks good". The tool maps the note to structured tags with severity, an acceptance hint, and
the next recommended review tool without calling an external model.

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

Mask paths are resolved through the same `--allowed-root` policy as input images. Dataset onboarding can also emit
inline `mask_polygons` or COCO `mask_rles` with uncompressed or compressed counts for segmentation samples.

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

## Review Packet

Use `build_review_packet` when the host needs one compact first-preview handoff for a real local dataset folder. It wraps
dataset onboarding, the safe preview template, the recommended next tool, the full review tool sequence, and the report
handoff resource:

```json
{
  "dataset_path": "/absolute/path/to/images",
  "task": "classification",
  "intensity": "low",
  "targets": ["image"],
  "max_images": 8
}
```

When `preview_ready` is true, validate `preview_request_template.request` with `validate_preview_request`, render it with
`render_preview_batch`, then follow `tool_sequence` through feedback, comparison, report export, and pipeline export. If
`preview_ready` is false, show `review_brief` and `remediation_actions` before attempting previews.

## Golden Evals

Run executable MCP scenarios locally before changing tool contracts:

```bash
uv run python scripts/run_golden_evals.py
```

The golden suite includes a real sample first-preview smoke, a Review Packet handoff flow, and a preview-request
troubleshooting scenario. They call `run_host_smoke_check`, `build_review_packet`, read
`albumentationsx://examples/first-preview`, validate filled preview requests, render deterministic local sample PNGs,
read preview manifests, compare runs with `quality_summary`, and delete generated runs through MCP stdio.

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
