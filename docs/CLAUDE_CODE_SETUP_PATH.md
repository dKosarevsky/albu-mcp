# Claude Code Setup Path

Setup status: `blocked_until_claude_cli_visible`
Host: `Claude Code`
Failure class: `claude_cli_missing`
CLI required: `true`
RC reopen allowed: `false`

## Setup Policy

Do not replay Claude Code P0 gates until the `claude` CLI is visible in the same shell/session that will own MCP configuration and tool discovery.

## Summary

- affected_gate_count: `2`
- blocked_gate_count: `2`
- setup_check_count: `6`

## MCP Config

```json
{
  "type": "stdio",
  "command": "uvx",
  "args": [
    "--from",
    "albumentationsx-mcp",
    "albumentationsx-mcp",
    "--allowed-root",
    "/absolute/path/to/images",
    "--artifact-root",
    "/absolute/path/to/albu-artifacts"
  ]
}
```

## Setup Checks

- `command -v claude`
- `claude --version`
- `uvx --from albumentationsx-mcp albumentationsx-mcp --help`
- `claude mcp add-json albumentationsx '{"type":"stdio","command":"uvx","args":["--from","albumentationsx-mcp","albumentationsx-mcp","--allowed-root","/absolute/path/to/images","--artifact-root","/absolute/path/to/albu-artifacts"]}'`
- `claude mcp get albumentationsx`
- `claude mcp list`

## Run Order

1. Install or expose Claude Code CLI on PATH.
2. Verify `claude --version` from the same terminal profile used for MCP setup.
3. Import the AlbumentationsX MCP stdio config with bounded roots.
4. Restart or refresh Claude Code MCP discovery.
5. List MCP tools and read albumentationsx://examples/client-smoke.
6. Call run_host_smoke_check, then run First 10 Minutes only if preview_ready=true.

## Affected Gates

| Gate | Evidence Status | Passed Command | Blocked Command |
| --- | --- | --- | --- |
| `first_10_minutes_replay` | `blocked` | `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed first_10_minutes_replay in a real MCP host UI.' --artifact docs/assets/demo/demo_report.md` | `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status blocked --date YYYY-MM-DD --evidence 'Claude Code CLI was not visible or could not start MCP before first_10_minutes_replay could pass.'` |
| `manual_host_ui` | `blocked` | `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed manual_host_ui in a real MCP host UI.'` | `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status blocked --date YYYY-MM-DD --evidence 'Claude Code CLI was not visible or could not start MCP before manual_host_ui could pass.'` |

## Acceptance Criteria

- `claude --version` succeeds in the operator shell.
- `claude mcp list` shows the AlbumentationsX MCP server.
- Claude Code can read albumentationsx://examples/client-smoke.
- run_host_smoke_check completes in Claude Code with preview_ready=true.
- Affected P0 gates have dated real-host evidence notes or artifacts.

## Record Commands

Passed evidence:
- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed first_10_minutes_replay in a real MCP host UI.' --artifact docs/assets/demo/demo_report.md`
- `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed manual_host_ui in a real MCP host UI.'`

Blocked evidence:
- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status blocked --date YYYY-MM-DD --evidence 'Claude Code CLI was not visible or could not start MCP before first_10_minutes_replay could pass.'`
- `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status blocked --date YYYY-MM-DD --evidence 'Claude Code CLI was not visible or could not start MCP before manual_host_ui could pass.'`

## Source Docs

- `docs/INSTALL.md`
- `examples/claude_code_preview_command.md`
- `docs/P0_HOST_UNBLOCK_PACK.md`
- `docs/HOST_EVIDENCE_RUNNER.md`
