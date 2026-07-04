# Session capture

Phase id: `session_capture`

Status: `blocked_until_setup_probe`

Writes records: `false`

## Goal

Prepare privacy-safe reviewer notes and a manifest template for Reviewer-observed real MCP host UI.

## Next Commands

- `albu-mcp evidence transcript-template`
- `albu-mcp evidence session-manifest --host Codex --date YYYY-MM-DD --reviewer 'Release operator'`
- `albu-mcp evidence session-folder --host Codex --date YYYY-MM-DD --reviewer 'Release operator'`
