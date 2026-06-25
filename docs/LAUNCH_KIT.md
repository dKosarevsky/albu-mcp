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
- Route host proof updates through `docs/HOST_MANUAL_RUNS.json` and regenerated reports.
