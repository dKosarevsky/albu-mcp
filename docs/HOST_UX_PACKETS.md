# Host UX Packets

Package: `albumentationsx-mcp==1.17.1`
Allowed root placeholder: `/absolute/path/to/images`
Artifact root placeholder: `/absolute/path/to/albu-artifacts`

Use these packets as copy-paste host setup guides. Replace placeholders before running.

## First-Run Prompt

```text
Run the AlbumentationsX MCP first-run flow.
1. Read albumentationsx://examples/client-smoke.
2. Call run_host_smoke_check.
3. Call inspect_dataset_quality on the local image folder.
4. Call build_review_packet.
5. Validate the generated preview request.
6. Render a small preview batch.
7. Compare baseline and candidate previews.
8. Interpret feedback such as 'example 8 is too noisy'.
9. Plan the preview review action.
10. Export the preview report or final pipeline.
```

## Claude Desktop

Edit the Claude Desktop MCP config, then restart Claude Desktop.

```json
{
  "mcpServers": {
    "albumentationsx": {
      "command": "uvx",
      "args": [
        "--from",
        "albumentationsx-mcp==1.17.1",
        "albumentationsx-mcp",
        "--allowed-root",
        "/absolute/path/to/images",
        "--artifact-root",
        "/absolute/path/to/albu-artifacts"
      ]
    }
  }
}
```

Expected tools:

- `run_host_smoke_check`
- `inspect_dataset_quality`
- `build_review_packet`
- `validate_preview_request`
- `render_preview_batch`
- `compare_preview_runs`
- `interpret_preview_feedback`
- `plan_preview_review`
- `export_preview_report`
- `export_pipeline`

Troubleshooting:

- Run `diagnose_environment` if the host lists tools but preview setup fails.
- Check `--allowed-root` when local paths are rejected.
- Check `--artifact-root` permissions when preview artifacts are missing.
- Record real host evidence for Claude Desktop only after the host UI completes the first-run prompt.

## Claude Code

Run the command in a shell where Claude Code is authenticated.

```bash
claude mcp add-json albumentationsx '{"type":"stdio","command":"uvx","args":["--from","albumentationsx-mcp==1.17.1","albumentationsx-mcp","--allowed-root","/absolute/path/to/images","--artifact-root","/absolute/path/to/albu-artifacts"]}'
```

Expected tools:

- `run_host_smoke_check`
- `inspect_dataset_quality`
- `build_review_packet`
- `validate_preview_request`
- `render_preview_batch`
- `compare_preview_runs`
- `interpret_preview_feedback`
- `plan_preview_review`
- `export_preview_report`
- `export_pipeline`

Troubleshooting:

- Run `diagnose_environment` if the host lists tools but preview setup fails.
- Check `--allowed-root` when local paths are rejected.
- Check `--artifact-root` permissions when preview artifacts are missing.
- Record real host evidence for Claude Code only after the host UI completes the first-run prompt.

## Cursor

Edit the Cursor MCP config, then Refresh MCP discovery.

```json
{
  "mcpServers": {
    "albumentationsx": {
      "command": "uvx",
      "args": [
        "--from",
        "albumentationsx-mcp==1.17.1",
        "albumentationsx-mcp",
        "--allowed-root",
        "/absolute/path/to/images",
        "--artifact-root",
        "/absolute/path/to/albu-artifacts"
      ]
    }
  }
}
```

Expected tools:

- `run_host_smoke_check`
- `inspect_dataset_quality`
- `build_review_packet`
- `validate_preview_request`
- `render_preview_batch`
- `compare_preview_runs`
- `interpret_preview_feedback`
- `plan_preview_review`
- `export_preview_report`
- `export_pipeline`

Troubleshooting:

- Run `diagnose_environment` if the host lists tools but preview setup fails.
- Check `--allowed-root` when local paths are rejected.
- Check `--artifact-root` permissions when preview artifacts are missing.
- Record real host evidence for Cursor only after the host UI completes the first-run prompt.

## Codex

Edit the Codex MCP config, then restart or reload the Codex session.

```toml
[mcp_servers.albumentationsx]
command = "uvx"
args = [
  "--from",
  "albumentationsx-mcp==1.17.1",
  "albumentationsx-mcp",
  "--allowed-root",
  "/absolute/path/to/images",
  "--artifact-root",
  "/absolute/path/to/albu-artifacts",
]
```

Expected tools:

- `run_host_smoke_check`
- `inspect_dataset_quality`
- `build_review_packet`
- `validate_preview_request`
- `render_preview_batch`
- `compare_preview_runs`
- `interpret_preview_feedback`
- `plan_preview_review`
- `export_preview_report`
- `export_pipeline`

Troubleshooting:

- Run `diagnose_environment` if the host lists tools but preview setup fails.
- Check `--allowed-root` when local paths are rejected.
- Check `--artifact-root` permissions when preview artifacts are missing.
- Record real host evidence for Codex only after the host UI completes the first-run prompt.

