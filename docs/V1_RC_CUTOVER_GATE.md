# V1 RC Cutover Gate

Package: `albumentationsx-mcp==1.15.0`
Release tag: `vX.Y.Z-rc.1`
Required hosts: `Codex, Claude Code`
Gate status: `blocked`
Cutover allowed: `false`
RC decision: `hold_rc`
Blocked reason: `p0_host_evidence_missing_or_blocked`

## Gate Policy

The RC cutover gate refuses release while any P0 real-host evidence gate is not passed.

## P0 Summary

- required_gate_count: `4`
- recorded_gate_count: `0`
- missing_gate_count: `0`
- blocked_gate_count: `4`

## Failed Gates

| Host | Gate | Record Status | Date | Evidence |
| --- | --- | --- | --- | --- |
| Codex | `first_10_minutes_replay` | `blocked` | `2026-06-28` | Codex CLI host run reached AlbumentationsX MCP discovery and read albumentationsx://examples/client-smoke, but run_host_smoke_check returned user cancelled MCP tool call twice; preview_ready was not confirmed. |
| Codex | `manual_host_ui` | `blocked` | `2026-06-28` | Codex CLI host listed AlbumentationsX MCP resources/tools and read client-smoke, but run_host_smoke_check was cancelled twice before preview_ready could be confirmed. |
| Claude Code | `first_10_minutes_replay` | `blocked` | `2026-06-28` | Claude Code host run could not start in this environment because claude CLI was not found in PATH; first-10-minutes replay was not executed. |
| Claude Code | `manual_host_ui` | `blocked` | `2026-06-28` | Claude Code manual host UI run could not start in this environment because claude CLI was not found in PATH; MCP tools/resources were not observed in Claude Code. |

## Preflight Commands

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
- `uv run python scripts/check_release_readiness.py`
- `uv build`

## Publish Commands

- none

## Blocked Publish Commands

- `git tag vX.Y.Z-rc.1`
- `git push origin vX.Y.Z-rc.1`
- `gh release create vX.Y.Z-rc.1 --prerelease --generate-notes`

## Source Docs

- `docs/P0_HOST_EVIDENCE_LEDGER.md`
- `docs/P0_EVIDENCE_REGENERATION_PACK.md`
- `docs/V1_RC_READINESS.md`
- `docs/V1_RC_AUTOMATION_PACK.md`

## Next Action

Do not tag or publish the RC; complete P0 real-host evidence and rerun this gate with --require-open.
