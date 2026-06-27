# AlbumentationsX MCP

Model Context Protocol server for [AlbumentationsX](https://github.com/albumentations-team/AlbumentationsX): transform
discovery, pipeline validation, deterministic previews, feedback loops, and reproducible exports for computer vision.

<!-- mcp-name: io.github.dKosarevsky/albu-mcp -->

[![CI](https://github.com/dKosarevsky/albu-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/dKosarevsky/albu-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/albumentationsx-mcp)](https://pypi.org/project/albumentationsx-mcp/)
[![Python](https://img.shields.io/badge/python-3.10--3.13-blue)](pyproject.toml)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-active-green)](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp)

## Purpose

AlbumentationsX MCP is a thin, typed MCP layer around existing AlbumentationsX primitives. It helps MCP hosts:

- discover transforms and schemas from `albu-spec`;
- recommend and validate augmentation pipelines;
- render local batch previews and compare preview runs;
- record concrete feedback such as `too_noisy:high`;
- export accepted pipelines and review reports.

The server does not execute arbitrary Python, fetch remote images, overwrite datasets, or train models. Local preview
access is bounded by `--allowed-root`, and generated artifacts are written under `--artifact-root`.

## Quick Start

Run the published server:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
```

For local development:

```bash
uv sync --all-extras --dev
uv run albumentationsx-mcp
```

For preview work, scope filesystem access explicitly:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp \
  --allowed-root /absolute/path/to/images \
  --artifact-root /absolute/path/to/albu-artifacts
```

Copyable host snippets are in [examples](examples/). Full setup is in [docs/INSTALL.md](docs/INSTALL.md); the guided
trial is [docs/FIRST_10_MINUTES.md](docs/FIRST_10_MINUTES.md).

## Host Workflow

After connecting an MCP host:

1. Read `albumentationsx://examples/client-smoke`.
2. Call `run_host_smoke_check`.
3. Continue only when `preview_ready` is true.
4. For a real folder, call `build_review_packet` to sample local images and get one first-preview handoff.
5. Replace or reuse the paths in `preview_request_template.request`.
6. Call `validate_preview_request` before rendering user-provided paths.
7. Call `render_preview_batch` on a small local image set.
8. Inspect the contact sheet, then use `plan_preview_review` to choose adjustment, audit, or export.

If preview setup fails, read `albumentationsx://diagnostics/guide` and call `diagnose_environment`. Troubleshooting
details and `remediation_actions` are documented in [docs/USAGE.md](docs/USAGE.md) and [docs/INSTALL.md](docs/INSTALL.md).

## Capabilities

- Transform search and schema inspection.
- Recipe and pipeline recommendation for classification, detection, segmentation, OCR, and balanced workflows.
- Pipeline validation and explanation before rendering.
- Preview request validation for missing files, outside-root paths, masks, and annotation counts.
- Read-only dataset quality inspection before rendering previews.
- Read-only dataset onboarding and review packets that build bbox/mask-aware first-preview templates.
- Deterministic single-image and batch previews with contact sheets.
- Preview comparison with `quality_summary` and suggested feedback tags.
- Concrete preview feedback, interactive tuning sessions, ranking, dataset scoring, and visual reports.
- Agent workflow resources, prompts, smoke checks, diagnostics, and release-safe contract snapshots.

The public MCP surface is kept stable through reviewed contract snapshots. Compatibility rules are in
[docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

The community guide was accepted upstream in [AlbumentationsX#289](https://github.com/albumentations-team/AlbumentationsX/pull/289);
source: [docs/integrations/mcp.md](https://github.com/albumentations-team/AlbumentationsX/blob/main/docs/integrations/mcp.md).

## Documentation

- [docs/INSTALL.md](docs/INSTALL.md): PyPI, MCP Registry, Claude Desktop, Claude Code, Cursor, Codex, bounded roots.
- [docs/FIRST_10_MINUTES.md](docs/FIRST_10_MINUTES.md): shortest path from install to preview, feedback, and export.
- [docs/HOST_PROOF_SPRINT.md](docs/HOST_PROOF_SPRINT.md), [docs/HOST_PROOF_SPRINT_CHECKLIST.md](docs/HOST_PROOF_SPRINT_CHECKLIST.md), [docs/HOST_EVIDENCE_SPRINT_BOARD.md](docs/HOST_EVIDENCE_SPRINT_BOARD.md), [docs/P0_HOST_RUNBOOK.md](docs/P0_HOST_RUNBOOK.md), [docs/P0_EVIDENCE_RECORDER.md](docs/P0_EVIDENCE_RECORDER.md), [docs/P0_HOST_EXECUTION_SPRINT.md](docs/P0_HOST_EXECUTION_SPRINT.md), [docs/P0_BLOCKER_TRIAGE.md](docs/P0_BLOCKER_TRIAGE.md), [docs/REAL_HOST_EVIDENCE_EXECUTION.md](docs/REAL_HOST_EVIDENCE_EXECUTION.md), [docs/HOST_UX_HARDENING_LOOP.md](docs/HOST_UX_HARDENING_LOOP.md), and [docs/HOST_FAILURE_COOKBOOK.md](docs/HOST_FAILURE_COOKBOOK.md): real host replay runbook, checklist, sprint board, P0 runbook, recorder, execution sprint, blocker triage, execution pack, hardening loop, and failure triage.
- [docs/USAGE.md](docs/USAGE.md): end-to-end MCP host workflow and tool details.
- [docs/RECIPES.md](docs/RECIPES.md): task-specific host recipes.
- [docs/ADOPTION.md](docs/ADOPTION.md), [docs/BETA_WORKFLOW_PACK.md](docs/BETA_WORKFLOW_PACK.md), [docs/BETA_FEEDBACK_INTAKE.md](docs/BETA_FEEDBACK_INTAKE.md), and [docs/BETA_VALIDATION_SPRINT.md](docs/BETA_VALIDATION_SPRINT.md): short trial, beta CV workflows, feedback intake, beta validation, host setup, workflow examples, and outreach copy.
- [docs/ADOPTION_PACKET.md](docs/ADOPTION_PACKET.md) and [docs/LAUNCH_KIT.md](docs/LAUNCH_KIT.md): generated public launch copy, distribution checklist, demo assets, and feedback intake.
- [docs/COMMUNITY_FEEDBACK.md](docs/COMMUNITY_FEEDBACK.md): privacy-safe GitHub issue intake.
- [docs/PRODUCT_DEPTH_BACKLOG.md](docs/PRODUCT_DEPTH_BACKLOG.md): post-P0 product-depth candidates driven by beta feedback buckets.
- [docs/NETWORK_GROWTH.md](docs/NETWORK_GROWTH.md), [docs/NETWORK_GROWTH_TRACKER.md](docs/NETWORK_GROWTH_TRACKER.md), [docs/PUBLIC_ADOPTION_LOOP.md](docs/PUBLIC_ADOPTION_LOOP.md), and [docs/ADOPTION_TRIAGE_REPORT.md](docs/ADOPTION_TRIAGE_REPORT.md): directory status, registry follow-up, and adoption loop.
- [docs/UPSTREAM_PR_PACKET.md](docs/UPSTREAM_PR_PACKET.md): upstream source for [AlbumentationsX#289](https://github.com/albumentations-team/AlbumentationsX/pull/289).
- [examples/distortion_review_workflow.md](examples/distortion_review_workflow.md): rejected noisy preview review loop.
- [docs/DEMO.md](docs/DEMO.md): generated preview comparison demo.
- [docs/HOST_ACCEPTANCE.md](docs/HOST_ACCEPTANCE.md), [docs/HOST_MATRIX.md](docs/HOST_MATRIX.md), [docs/HOST_UX_PACKETS.md](docs/HOST_UX_PACKETS.md), and [docs/HOST_ACCEPTANCE_EVIDENCE.md](docs/HOST_ACCEPTANCE_EVIDENCE.md): MCP host acceptance status.
- [docs/V1_READINESS.md](docs/V1_READINESS.md): v1 compatibility and release audit.
- [docs/V1_LAUNCH_REPORT.md](docs/V1_LAUNCH_REPORT.md), [docs/V1_DECISION_REPORT.md](docs/V1_DECISION_REPORT.md), [docs/V1_RC_READINESS.md](docs/V1_RC_READINESS.md), [docs/V1_RC_RELEASE_PACKET.md](docs/V1_RC_RELEASE_PACKET.md), [docs/V1_RC_CUTOVER_CHECKLIST.md](docs/V1_RC_CUTOVER_CHECKLIST.md), and [docs/P0_EVIDENCE_STATUS.md](docs/P0_EVIDENCE_STATUS.md): current v1 launch blockers, go/no-go decision, RC gate, gated RC packet, RC cutover checklist, and P0 evidence status.
- [docs/RELEASE.md](docs/RELEASE.md): PyPI, GitHub Release, and MCP Registry publication process.
- [CHANGELOG.md](CHANGELOG.md): release history.
- [server.json](server.json): public MCP Registry metadata.
- [evals/golden_mcp_scenarios.yaml](evals/golden_mcp_scenarios.yaml): executable MCP scenarios.

Operational scripts live in [scripts](scripts/) and are covered by the verification commands below.

## Verification

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/validate_host_manual_runs.py
uv run python scripts/check_host_acceptance_report.py
uv run python scripts/check_first_10_minutes.py
uv run python scripts/check_host_proof_sprint.py
uv run python scripts/check_contract_snapshots.py
uv run python scripts/check_demo_assets.py --output-dir docs/assets/demo --check
uv run python scripts/check_release_readiness.py
uv run python scripts/run_golden_evals.py
uv run python scripts/check_mcp_registry_status.py
uv run python scripts/check_directory_presence.py
uv run python scripts/export_launch_kit.py --output docs/LAUNCH_KIT.md
uv build
```
