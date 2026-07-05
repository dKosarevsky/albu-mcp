---
name: albumentationsx-mcp
description: Use when Codex needs to install, configure, or operate AlbumentationsX MCP from agent hosts for computer-vision augmentation previews, feedback-driven tuning, bounded local dataset review, or evidence-backed adoption workflows.
---

# AlbumentationsX MCP

## Overview

AlbumentationsX MCP is the MCP server; this skill is the agent playbook for using it safely. Keep all preview work local, bounded, reproducible, and explicit about what is real user evidence versus generated fixtures.

## Install

Install the server with:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
```

For real preview work, require bounded roots:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp \
  --allowed-root /absolute/path/to/images \
  --artifact-root /absolute/path/to/albu-artifacts
```

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

## Evidence Workflows

Use operator commands only when the user is doing release, adoption, or product evidence work:

- `albu-mcp activation real-adoption-cycle`
- `albu-mcp activation product-fix-closure-pipeline`
- `albu-mcp evidence import-wizard`

If a preview setup fails, read `albumentationsx://diagnostics/guide`, call `diagnose_environment`, and follow its remediation actions before attempting another render.
