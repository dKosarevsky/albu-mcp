---
name: albumentationsx-mcp
description: Use when Codex needs to install, configure, or operate AlbumentationsX MCP from agent hosts for computer-vision augmentation previews, feedback-driven tuning, bounded local dataset review, or evidence-backed adoption workflows.
---

# AlbumentationsX MCP

## Overview

Use this playbook to keep AlbumentationsX MCP previews bounded and distinguish real evidence from generated fixtures.

## Install

Install:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
```

Require bounded roots:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp \
  --allowed-root /absolute/path/to/images \
  --artifact-root /absolute/path/to/albu-artifacts
```

## First Run Prompt

Use this as the first host task:

```text
Use AlbumentationsX MCP on `DATASET_PATH`. Use `ALLOWED_ROOT` for image access and `ARTIFACT_ROOT` for generated outputs. Read `albumentationsx://examples/client-smoke`, call `run_host_smoke_check`, and continue only when `preview_ready` is true. If `preview_ready` is false, call `diagnose_environment` and stop before rendering. Then call `plan_dataset_onboarding`, `build_review_packet`, `validate_preview_request`, and `render_preview_batch`. Render at most 6 images on the first pass. Show the contact sheet path and ask for concrete feedback before `adjust_pipeline` or `export_pipeline`.
```

## Host Config Hints

- Codex plugin mode uses `.codex-plugin/plugin.json` and `.mcp.json`; it starts the pinned server but grants no roots.
- Set `ALBU_MCP_ALLOWED_ROOTS` and `ALBU_MCP_ARTIFACT_ROOT`, or use explicit absolute host args. Never rely on the working directory.
- Restart the host, run `run_host_smoke_check`, and stop before rendering when `preview_ready` is false.

## Host Workflow

1. Read `albumentationsx://examples/client-smoke`.
2. Call `run_host_smoke_check`; continue only when `preview_ready` is true.
3. For a real image folder, call `plan_dataset_onboarding`, then `build_review_packet` to get a small first-preview handoff.
4. Validate user paths with `validate_preview_request` before rendering.
5. Call `render_preview_batch` on a small local sample and inspect the contact sheet.
6. Capture concrete feedback with `record_preview_feedback`; use tags such as `too_noisy:high`.
7. Call `adjust_pipeline`, re-render, and compare before accepting changes.
8. Export only reviewed work with `export_pipeline` or the report/export tools requested by the user.

## Safety Rules

- Do not train models, overwrite datasets, or fetch remote images.
- Do not expose private local paths, filenames, or image contents in public reports.
- Do not treat generated fixtures, contact sheets, or rehearsals as real beta evidence.
- Keep all image reads under `--allowed-root` and all generated files under `--artifact-root`.
- Re-run validation after changing paths, masks, bboxes, labels, or annotation formats.

## Stop Conditions

- Missing real dataset path: ask for one.
- Path outside `--allowed-root`: refuse that path and ask for a bounded path.
- User asks for many variants: render a small first batch before expanding.

## Evidence Workflows

For release, adoption, or product evidence, follow the generated pack README and use:

- `albu-mcp activation real-adoption-cycle`
- `albu-mcp activation product-fix-closure-pipeline`
- `albu-mcp evidence execution-pack --date YYYY-MM-DD --reviewer "Release operator" --output-dir evidence-session --format markdown`
- `albu-mcp evidence execution-pack-audit --input-dir evidence-session`
- `albu-mcp evidence execution-pack-progress --input-dir evidence-session`
- `albu-mcp evidence execution-pack-status --input-dir evidence-session --format markdown --output evidence-session/status.md`
- `albu-mcp evidence preflight`
- `albu-mcp evidence import-wizard`

If preview setup fails, read `albumentationsx://diagnostics/guide`, call `diagnose_environment`, then remediate before rendering.
