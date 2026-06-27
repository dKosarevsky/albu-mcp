# AlbumentationsX MCP Adoption Packet

AlbumentationsX MCP for batch previews, compare preview runs, segmentation masks, and exports.

## Install

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
```

For local previews:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp --allowed-root /absolute/path/to/images --artifact-root /absolute/path/to/albu-artifacts
```

## Public Links

- Repository: https://github.com/dKosarevsky/albu-mcp
- PyPI: https://pypi.org/project/albumentationsx-mcp/
- MCP Registry: https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp
- Upstream docs PR: AlbumentationsX#289 (https://github.com/albumentations-team/AlbumentationsX/pull/289)
- Launch Kit: docs/LAUNCH_KIT.md

## Host Coverage

- Claude Desktop
- Claude Code
- Cursor
- Codex

## First Dataset Workflow

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

## Short Launch Copy

AlbumentationsX MCP lets MCP hosts inspect a local computer-vision dataset, build a safe first-preview request, render contact sheets, capture concrete feedback, and export reproducible AlbumentationsX pipelines without giving the host arbitrary Python execution.

## Privacy Note

Keep private datasets local. Use `--allowed-root` to scope image access and share only redacted artifacts.
