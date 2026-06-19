# MCP Host Acceptance Matrix

Use this matrix after releases that change tools, resources, prompts, package metadata, or local preview behavior.
Automated stdio, snapshot, release, PyPI, and MCP Registry checks run in CI. Manual app-level host checks are intentionally
small: one local image under `--allowed-root`, one temporary `--artifact-root`, and the PyPI command from
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
5. `export_preview_report` links exported Markdown tuning session artifacts when matching sessions exist.
6. `export_tuning_session` returns Markdown or JSON content plus artifact metadata suitable for handoff.

Recorded coverage:

- Automated: pytest, golden stdio evals, output contract snapshots, release build, PyPI publish check, and MCP Registry
  metadata publish check.
- Manual host UI: pending per host unless a dated run note is added below this matrix.

To produce a reviewable evidence artifact without overstating manual coverage:

```bash
uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md
uv run python scripts/check_host_acceptance_report.py
```

Add dated manual notes to `docs/HOST_MANUAL_RUNS.json`; supported statuses are `passed`, `blocked`, and `pending`.
Validate them with `uv run python scripts/validate_host_manual_runs.py`. The JSON shape is documented in
`docs/HOST_MANUAL_RUNS.schema.json`.
Use `uv run python scripts/record_host_manual_run.py ...` to add or replace one host record without introducing
duplicate host entries.
