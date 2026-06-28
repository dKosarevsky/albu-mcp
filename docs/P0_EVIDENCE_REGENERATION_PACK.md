# P0 Evidence Regeneration Pack

Package: `albumentationsx-mcp==1.15.0`
Records path: `docs/HOST_MANUAL_RUNS.json`
Target hosts: `Codex, Claude Code`
Pack status: `blocked_until_p0_evidence`
RC regeneration allowed: `false`
Blocked reason: `p0_host_evidence_missing_or_blocked`

## Gate Policy

Regenerate RC cutover artifacts only after real P0 host evidence records pass. Do not treat generated RC artifacts as release-ready while this pack is blocked.

## Summary

- required_gate_count: `4`
- recorded_gate_count: `0`
- missing_gate_count: `0`
- blocked_gate_count: `4`

## Gate Records

| Host | Gate | Record Status | Date | Evidence |
| --- | --- | --- | --- | --- |
| Codex | `first_10_minutes_replay` | `blocked` | `2026-06-28` | Codex CLI host run reached AlbumentationsX MCP discovery and read albumentationsx://examples/client-smoke, but run_host_smoke_check returned user cancelled MCP tool call twice; preview_ready was not confirmed. |
| Codex | `manual_host_ui` | `blocked` | `2026-06-28` | Codex CLI host listed AlbumentationsX MCP resources/tools and read client-smoke, but run_host_smoke_check was cancelled twice before preview_ready could be confirmed. |
| Claude Code | `first_10_minutes_replay` | `blocked` | `2026-06-28` | Claude Code host run could not start in this environment because claude CLI was not found in PATH; first-10-minutes replay was not executed. |
| Claude Code | `manual_host_ui` | `blocked` | `2026-06-28` | Claude Code manual host UI run could not start in this environment because claude CLI was not found in PATH; MCP tools/resources were not observed in Claude Code. |

## Safe Anytime Commands

- `uv run python scripts/check_p0_host_run_preflight.py`
- `uv run python scripts/verify_host_evidence_import.py`
- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md`
- `uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md`
- `uv run python scripts/check_release_readiness.py`

## Gated Regeneration Commands

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md`
- `uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md`
- `uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md`
- `uv run python scripts/export_v1_rc_release_packet.py --output docs/V1_RC_RELEASE_PACKET.md`
- `uv run python scripts/export_v1_rc_cutover_checklist.py --output docs/V1_RC_CUTOVER_CHECKLIST.md`
- `uv run python scripts/export_v1_rc_automation_pack.py --output docs/V1_RC_AUTOMATION_PACK.md`
- `uv run python scripts/export_v1_growth_cutover_report.py --output docs/V1_GROWTH_CUTOVER_REPORT.md`
- `uv run python scripts/check_release_readiness.py`

## Source Docs

- `docs/P0_HOST_RUN_SESSION.md`
- `docs/P0_HOST_RUN_PREFLIGHT.md`
- `docs/P0_EVIDENCE_IMPORT_GUIDE.md`
- `docs/P0_HOST_EVIDENCE_LEDGER.md`
- `docs/V1_RC_READINESS.md`

## Next Action

Complete real P0 host runs, verify candidate evidence, and record passed gates before RC cutover.
