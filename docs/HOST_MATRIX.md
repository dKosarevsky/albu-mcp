# MCP Host Acceptance Matrix

Use this matrix after releases that change tools, resources, prompts, package metadata, or local preview behavior. Keep
the manual run small: one local image under `--allowed-root`, one temporary `--artifact-root`, and the PyPI command from
`docs/INSTALL.md`.

| Host | Connection check | Preview check | Session check | Notes |
| --- | --- | --- | --- | --- |
| Claude Desktop | Restart after config changes, then list tools and read `albumentationsx://examples/client-smoke`. | Run `run_host_smoke_check`, `validate_preview_request`, and `render_preview_batch`. | Call `start_tuning_session`, `record_tuning_session_step`, `close_tuning_session`, and `export_tuning_session`. | Confirm absolute paths are visible to the desktop app process. |
| Claude Code | Add the preview command from `examples/claude_code_preview_command.md`. | Confirm `run_first_preview_review` can guide the first preview. | Call `archive_tuning_session` on a completed session. | Prefer shell-visible paths under the current workspace or an explicit allowed root. |
| Cursor | Use `examples/cursor_preview_mcp_config.json` and refresh MCP discovery. | Confirm Cursor lists `validate_preview_request`, `render_preview_batch`, and `compare_preview_runs`. | Call `list_tuning_sessions` with `status="accepted"` and `status="archived"`. | Reopen the MCP panel after package upgrades. |
| Codex | Use `examples/codex_preview_mcp_config.toml`. | Read workflow resources before calling preview tools. | Call `cleanup_tuning_sessions` with `include_active=false` and verify active sessions remain. | Keep generated artifacts under a temporary root during acceptance. |

Minimum release acceptance:

1. `albumentationsx://capabilities` lists the expected tools, prompts, resources, roots, and limits.
2. `diagnose_environment` returns either `status="ok"` or actionable `remediation_actions`.
3. `validate_preview_request` rejects missing and outside-root paths before rendering.
4. `export_preview_report` includes contact sheets, concrete feedback, and interactive tuning session timelines when
   matching sessions exist.
5. `export_tuning_session` returns Markdown or JSON suitable for handoff.
