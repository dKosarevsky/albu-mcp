# Setup probe

Phase id: `setup_probe`

Status: `ready_to_run`

Writes records: `false`

## Goal

Verify the selected MCP host can see the local server and allowed roots before evidence capture.

## Next Commands

- `albu-mcp host setup-probe --host Codex --live --format json`
- `albu-mcp activation acquisition-cycle --host Codex --format json`
