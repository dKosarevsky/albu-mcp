# Host Evidence Capture Kit

Kit status: `operator_capture_required`
Target hosts: `Codex, Claude Code`

## Non-Fabrication Policy

Record passed only after a reviewer observes the real MCP host UI flow.
Do not record `passed` from generated smoke output.

## Summary

- target_host_count: `2`
- required_gate_count: `4`
- blocked_gate_count: `2`
- passed_gate_count: `2`

## Pre-Capture Commands

- `uv run python scripts/check_host_setup_probe.py --live --format json`
- `uv run python scripts/check_p0_host_run_preflight.py`
- `uv run python scripts/export_manual_host_acceptance_packet.py --host '<host>' --output /tmp/albu-host-<host>.md`

## Capture Lanes

| Host | Capture Status | Blocker | Gates | First Action | Next Doc |
| --- | --- | --- | --- | --- | --- |
| `Codex` | `blocked_until_operator_run` | `codex_tool_call_cancelled` |  | Run Codex with visible MCP tool approval and complete run_host_smoke_check. | `docs/CODEX_CANCELLATION_TRIAGE.md` |
| `Claude Code` | `blocked_until_operator_run` | `claude_cli_missing` | `first_10_minutes_replay`, `manual_host_ui` | Install or expose the Claude Code CLI, then import the AlbumentationsX MCP config. | `docs/CLAUDE_CODE_SETUP_PATH.md` |

## Record Commands

`scripts/record_host_manual_run.py` is the only P0 evidence writer.
### Codex

Passed evidence:

Blocked evidence:

### Claude Code

Passed evidence:
- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed first_10_minutes_replay in a real MCP host UI.' --artifact docs/assets/demo/demo_report.md`
- `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed manual_host_ui in a real MCP host UI.'`

Blocked evidence:
- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status blocked --date YYYY-MM-DD --evidence 'Claude Code CLI was not visible or could not start MCP before first_10_minutes_replay could pass.'`
- `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status blocked --date YYYY-MM-DD --evidence 'Claude Code CLI was not visible or could not start MCP before manual_host_ui could pass.'`

## Acceptance Criteria

- The reviewer sees the MCP host list AlbumentationsX MCP tools/resources.
- The reviewer sees run_host_smoke_check complete in the host UI.
- The reviewer sees preview_ready true before first-preview work.
- The record command includes only redacted evidence and artifact references.

## Post-Capture Commands

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md`
- `uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md`
- `uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json`

## Source Docs

- `docs/REAL_HOST_EVIDENCE_COMMAND_CENTER.md`
- `docs/P0_HOST_EVIDENCE_RECOVERY.md`
- `docs/P0_EVIDENCE_RECORDER.md`
- `docs/HOST_MANUAL_RUNS.json`
