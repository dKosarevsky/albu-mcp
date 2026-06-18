# Host Acceptance Checklist

Use this checklist after each public release that changes installation, host workflow, or MCP Registry metadata.
Use [HOST_MATRIX.md](HOST_MATRIX.md) for per-host manual acceptance details.

Generate a reviewable local evidence artifact before and after manual host runs:

```bash
uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md
```

The generated report records automated coverage and keeps host UI status `pending` until a dated manual run note is
added by a reviewer in `docs/HOST_MANUAL_RUNS.json`.

Validate manual run records before regenerating evidence:

```bash
uv run python scripts/validate_host_manual_runs.py
```

The JSON shape is documented in `docs/HOST_MANUAL_RUNS.schema.json`.

Manual run note format:

```json
{
  "host": "Codex",
  "status": "passed",
  "date": "2026-06-19",
  "evidence": "Codex app listed tools, read workflow resources, and ran run_host_smoke_check."
}
```

## MCP Registry card

- Latest Registry entry resolves as `io.github.dKosarevsky/albu-mcp`.
- Latest version matches `pyproject.toml`, `server.json`, and the release tag.
- Title is `AlbumentationsX MCP`.
- Description stays under the Registry limit and mentions batch previews plus compare preview runs.
- Icon is the Albumentations GitHub avatar PNG:
  `https://avatars.githubusercontent.com/u/57894582?s=200&v=4`.
- Homepage opens the project README.
- Package metadata points to PyPI package `albumentationsx-mcp` over `stdio`.
- Required environment variables are not marked as secrets.

## Common host flow

For every host, use a small local image under `--allowed-root` and a temporary `--artifact-root`.

1. Install from PyPI with `uvx --from albumentationsx-mcp albumentationsx-mcp`.
2. Connect the MCP host using the matching example config.
3. List tools and resources.
4. Read `albumentationsx://examples/first-preview`.
5. Call `run_host_smoke_check`.
6. Fill the returned `preview_request_template.request` with a real local image path.
7. Call `validate_preview_request`.
8. Call `render_preview_batch` only when validation returns `valid: true`.
9. Open the generated contact sheet and manifest.
10. Call `adjust_pipeline` and render a candidate from the same input set.
11. Call `compare_preview_runs`.
12. Call `start_tuning_session` and `record_tuning_session_step`.
13. Call `close_tuning_session` with the final accepted or rejected status.
14. Call `export_tuning_session` and confirm the accepted candidate appears in the exported content.
15. Call `export_pipeline` for a complete loop.

## Host-specific checks

### Claude Desktop

- Example config: `examples/claude_desktop_pypi_config.json`.
- Preview config: `examples/claude_desktop_preview_config.json`.
- Restart the app after changing config.
- Confirm the host can read `albumentationsx://diagnostics/guide` when preview setup is blocked.

### Claude Code

- Example command: `examples/claude_code_preview_command.md`.
- Confirm the host can call `run_first_preview_review`.
- Confirm shell-visible paths are absolute and under `--allowed-root`.

### Cursor

- Example config: `examples/cursor_mcp_config.json`.
- Preview config: `examples/cursor_preview_mcp_config.json`.
- Confirm Cursor can list `render_preview_batch`, `validate_preview_request`, and `run_host_smoke_check`.

### Codex

- Example config: `examples/codex_mcp_config.toml`.
- Preview config: `examples/codex_preview_mcp_config.toml`.
- Confirm Codex can read workflow resources before calling tools.

## Failure acceptance

A host run is acceptable only when failures are explicit and actionable:

- Missing image paths are reported by `validate_preview_request`.
- Paths outside `--allowed-root` are rejected before rendering.
- Missing or invalid masks are reported with mask-specific codes.
- Diagnostics include `remediation_actions`.
- No preview writes outside `--artifact-root`.
