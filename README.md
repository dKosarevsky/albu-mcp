# AlbumentationsX MCP

Model Context Protocol server for [AlbumentationsX](https://github.com/albumentations-team/AlbumentationsX):
transform discovery, pipeline validation, deterministic previews, feedback loops, and reproducible exports for computer
vision augmentation work.

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

Copyable host snippets are in [examples](examples/). Full host setup is in [docs/INSTALL.md](docs/INSTALL.md).

## Host Workflow

After connecting an MCP host:

1. Read `albumentationsx://examples/client-smoke`.
2. Call `run_host_smoke_check`.
3. Continue only when `preview_ready` is true.
4. For a real folder, call `plan_dataset_onboarding` to sample local images safely.
5. Replace or reuse the paths in `preview_request_template.request`.
6. Call `validate_preview_request` before rendering user-provided paths.
7. Call `render_preview_batch` on a small local image set.
8. Inspect the contact sheet, then use `adjust_pipeline`, `compare_preview_runs`, and `export_pipeline`.

If preview setup fails, read `albumentationsx://diagnostics/guide` and call `diagnose_environment`. Troubleshooting
details and `remediation_actions` are documented in [docs/USAGE.md](docs/USAGE.md) and [docs/INSTALL.md](docs/INSTALL.md).

## Capabilities

- Transform search and schema inspection.
- Recipe and pipeline recommendation for classification, detection, segmentation, OCR, and balanced workflows.
- Pipeline validation and explanation before rendering.
- Preview request validation for missing files, outside-root paths, masks, and annotation counts.
- Read-only dataset onboarding that samples local folders and builds first-preview request templates.
- Deterministic single-image and batch previews with contact sheets.
- Preview comparison with `quality_summary` and suggested feedback tags.
- Concrete preview feedback, interactive tuning sessions, ranking, dataset scoring, and visual reports.
- Agent workflow resources, prompts, smoke checks, diagnostics, and release-safe contract snapshots.

The public MCP surface is kept stable through reviewed contract snapshots. Compatibility rules are in
[docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## Documentation

- [docs/INSTALL.md](docs/INSTALL.md): PyPI, MCP Registry, Claude Desktop, Claude Code, Cursor, Codex, bounded roots.
- [docs/USAGE.md](docs/USAGE.md): end-to-end MCP host workflow and tool details.
- [docs/RECIPES.md](docs/RECIPES.md): task-specific host recipes.
- [docs/COMMUNITY_FEEDBACK.md](docs/COMMUNITY_FEEDBACK.md): privacy-safe GitHub issue intake for host and workflow
  feedback.
- [docs/NETWORK_GROWTH.md](docs/NETWORK_GROWTH.md): public directory status, registry follow-up, and outreach plan.
- [docs/UPSTREAM_PR_PACKET.md](docs/UPSTREAM_PR_PACKET.md): copyable community integration packet for AlbumentationsX
  docs if maintainers approve it.
- [examples/distortion_review_workflow.md](examples/distortion_review_workflow.md): rejected noisy preview review loop.
- [docs/DEMO.md](docs/DEMO.md): generated preview comparison demo.
- [docs/HOST_ACCEPTANCE.md](docs/HOST_ACCEPTANCE.md), [docs/HOST_MATRIX.md](docs/HOST_MATRIX.md), and
  [docs/HOST_ACCEPTANCE_EVIDENCE.md](docs/HOST_ACCEPTANCE_EVIDENCE.md): MCP host acceptance status.
- [docs/V1_READINESS.md](docs/V1_READINESS.md): v1 compatibility and release audit.
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
uv run python scripts/check_contract_snapshots.py
uv run python scripts/check_demo_assets.py --output-dir docs/assets/demo --check
uv run python scripts/check_release_readiness.py
uv run python scripts/run_golden_evals.py
uv run python scripts/check_mcp_registry_status.py
uv run python scripts/check_directory_presence.py
uv build
```
