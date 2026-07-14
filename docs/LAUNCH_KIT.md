# AlbumentationsX MCP Launch Kit

Use this packet when publishing, submitting, or sharing AlbumentationsX MCP.

## Primary Links

- Repository: https://github.com/dKosarevsky/albu-mcp
- PyPI: https://pypi.org/project/albumentationsx-mcp/
- MCP Registry: https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp
- Upstream docs PR: AlbumentationsX#289 (https://github.com/albumentations-team/AlbumentationsX/pull/289)

## Install

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
```

Preview-safe local run:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp --allowed-root /absolute/path/to/images --artifact-root /absolute/path/to/albu-artifacts
```

## Short Launch Copy

AlbumentationsX MCP connects MCP hosts to local computer-vision augmentation workflows: inspect dataset health, render bounded preview contact sheets, compare candidates, capture feedback, and export reproducible AlbumentationsX pipelines without arbitrary Python execution.

## Audience Campaigns

Automated preparation stops at this document. Publication: `manual only`. Run one campaign at a time, keep its destination fixed for seven days, and record only aggregate or voluntarily submitted evidence.

### classification-robustness

- Audience: Classification practitioners testing robustness without destroying label semantics
- Problem: Random augmentation policies can make objects unrecognizable before anyone reviews them.
- Prompt: "Inspect a small allowed image folder, render several medium-intensity robustness variants, compare them, reduce any variant tagged too_noisy:high, and export only the accepted pipeline."
- Artifact: `docs/assets/demo/comparison_contact_sheet.png`
- Destination: https://albumentations.ai/docs/integrations/mcp/?utm_source=community&utm_medium=manual&utm_campaign=classification-robustness
- Success signal: One voluntary report of a user rendering, rejecting, adjusting, and accepting a first preview.

### detection-bbox-safety

- Audience: Object-detection teams reviewing COCO or Pascal VOC augmentation safety
- Problem: Geometric transforms can silently drop or misalign bounding boxes.
- Prompt: "Inspect a safe detection fixture, recommend a low-intensity image+bboxes recipe, render bbox overlays, compare quality with the detection profile, and export only if every reviewed box remains."
- Artifact: `docs/RECIPES.md#detection-annotation-review`
- Destination: https://albumentations.ai/docs/integrations/mcp/?utm_source=community&utm_medium=manual&utm_campaign=detection-bbox-safety
- Success signal: One voluntary report of an accepted bbox-aware preview with bbox_retention_ratio equal to 1.0.

### segmentation-mask-safety

- Audience: Segmentation teams validating mask-aware geometric augmentation
- Problem: A plausible-looking image preview can hide mask coverage loss or misalignment.
- Prompt: "Inspect a safe segmentation fixture, recommend a low-intensity image+mask recipe, render mask overlays, compare with the segmentation quality profile, and reject any candidate with coverage loss."
- Artifact: `docs/RECIPES.md#segmentation-mask-review`
- Destination: https://albumentations.ai/docs/integrations/mcp/?utm_source=community&utm_medium=manual&utm_campaign=segmentation-mask-safety
- Success signal: One voluntary report of an accepted mask-aware preview without candidate_mask_coverage_drop.

## Measurement

Capture the aggregate baseline before publishing and compare it after seven days:

```bash
GH_TOKEN="$(gh auth token)" uv run python scripts/export_growth_report.py --output /tmp/albu-growth.md
```

## Demo Assets

- `docs/assets/demo/contact_sheet.png`
- `docs/assets/demo/comparison_contact_sheet.png`
- `docs/assets/demo/demo_report.md`

## First Workflow To Show

1. `run_host_smoke_check`
1. `inspect_dataset_quality`
1. `build_review_packet`
1. `validate_preview_request`
1. `render_preview_batch`
1. `compare_preview_runs`
1. `interpret_preview_feedback`
1. `plan_preview_review`
1. `export_preview_report`
1. `export_pipeline`

## Proof Status

- Ready for v1: `false`
- Blocker `manual_host_ui_pending`: At least one supported host lacks passed manual UI evidence.
- Blocker `first_10_minutes_replay_pending`: At least one supported host lacks passed First 10 Minutes replay evidence.

## Proof Docs

- `docs/HOST_PROOF_SPRINT.md`
- `docs/HOST_PROOF_SPRINT_CHECKLIST.md`
- `docs/V1_LAUNCH_REPORT.md`
- `docs/HOST_ACCEPTANCE_EVIDENCE.md`

## Growth Docs

- `docs/GROWTH.md`
- `docs/NETWORK_GROWTH.md`
- `docs/NETWORK_GROWTH_TRACKER.md`
- `docs/PUBLIC_ADOPTION_LOOP.md`

## Feedback Intake

- `.github/ISSUE_TEMPLATE/host-acceptance.yml`
- `.github/ISSUE_TEMPLATE/workflow-feedback.yml`
- `.github/ISSUE_TEMPLATE/dataset-health.yml`
- `.github/ISSUE_TEMPLATE/feature-request.yml`

## Distribution Checklist

- Keep `server.json`, PyPI, README, and MCP Registry copy aligned.
- Share demo assets only when they are synthetic or safe to publish.
- Link upstream AlbumentationsX documentation instead of duplicating long setup prose.
- Publish campaign copy manually; never automate third-party posts or imply upstream authorship.
- Route host proof updates through `docs/HOST_MANUAL_RUNS.json` and regenerated reports.
