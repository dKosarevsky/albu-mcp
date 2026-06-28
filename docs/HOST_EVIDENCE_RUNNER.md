# Host Evidence Runner

Runner status: `blocked_until_p0_evidence_passes`
Preflight status: `passed`
RC reopen allowed: `false`

## Runner Policy

Run this packet in real MCP host UI sessions only; generated smoke output is not accepted as passed host evidence.

## Summary

- target_host_count: `2`
- runner_lane_count: `4`
- blocked_lane_count: `4`
- preflight_check_count: `7`

## Preflight Commands

- `uv run python scripts/check_p0_host_run_preflight.py`
- `uv run python scripts/export_manual_host_acceptance_packet.py --host '<host>' --output /tmp/albu-host-<host>.md`

## Host Lanes

| Host | Lane Status | Gates | Prompt |
| --- | --- | --- | --- |
| Codex | `blocked_evidence_required` | `first_10_minutes_replay`, `manual_host_ui` | In Codex, list AlbumentationsX MCP tools, read albumentationsx://examples/client-smoke, call run_host_smoke_check, then run the First 10 Minutes workflow only if preview_ready is true. |
| Claude Code | `blocked_evidence_required` | `first_10_minutes_replay`, `manual_host_ui` | In Claude Code, list AlbumentationsX MCP tools, read albumentationsx://examples/client-smoke, call run_host_smoke_check, then run the First 10 Minutes workflow only if preview_ready is true. |

## Record Commands

### Codex

Passed evidence:
- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex completed first_10_minutes_replay in a real MCP host UI.' --artifact docs/assets/demo/demo_report.md`
- `uv run python scripts/record_host_manual_run.py --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex completed manual_host_ui in a real MCP host UI.'`

Blocked evidence:
- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status blocked --date YYYY-MM-DD --evidence 'Codex could not complete first_10_minutes_replay; record the first reviewer-observed blocker only.'`
- `uv run python scripts/record_host_manual_run.py --host Codex --status blocked --date YYYY-MM-DD --evidence 'Codex could not complete manual_host_ui; record the first reviewer-observed blocker only.'`

### Claude Code

Passed evidence:
- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed first_10_minutes_replay in a real MCP host UI.' --artifact docs/assets/demo/demo_report.md`
- `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed manual_host_ui in a real MCP host UI.'`

Blocked evidence:
- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status blocked --date YYYY-MM-DD --evidence 'Claude Code could not complete first_10_minutes_replay; record the first reviewer-observed blocker only.'`
- `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status blocked --date YYYY-MM-DD --evidence 'Claude Code could not complete manual_host_ui; record the first reviewer-observed blocker only.'`

## Post-Run Commands

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_host_evidence_runner.py --output docs/HOST_EVIDENCE_RUNNER.md`
- `uv run python scripts/export_p0_host_unblock_pack.py --output docs/P0_HOST_UNBLOCK_PACK.md`
- `uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md`
- `uv run python scripts/export_rc_cutover_recovery_plan.py --output docs/RC_CUTOVER_RECOVERY_PLAN.md`
- `uv run python scripts/check_release_readiness.py`

## Source Docs

- `docs/P0_HOST_UNBLOCK_PACK.md`
- `docs/P0_HOST_RUN_PREFLIGHT.md`
- `docs/P0_HOST_RUN_SESSION.md`
- `docs/HOST_MANUAL_RUNS.json`
