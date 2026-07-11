# Real Host Evidence Command Center

Command center status: `blocked_until_real_host_runs`
Next operator action: Run the host setup probe live, then execute the first blocked host lane.

## Non-Fabrication Policy

Only reviewer-observed real MCP host UI runs can satisfy P0 gates.
Record only redacted, reviewer-observed host UI evidence.

## Summary

- target_host_count: `1`
- required_gate_count: `4`
- passed_gate_count: `2`
- blocked_gate_count: `2`
- setup_probe_check_count: `6`
- runner_lane_count: `2`

## Blocked Hosts

- `Codex`
- `Claude Code`

## Host Lanes

| Host | Status | Blocker | Gates | First Action | Next Doc |
| --- | --- | --- | --- | --- | --- |
| Codex | `codex_evidence_recorded` | `codex_tool_call_cancelled` |  | Run Codex with visible MCP tool approval and complete run_host_smoke_check. | `docs/CODEX_CANCELLATION_TRIAGE.md` |
| Claude Code | `blocked_until_claude_cli_visible` | `claude_cli_missing` | `first_10_minutes_replay`, `manual_host_ui` | Install or expose the Claude Code CLI, then import the AlbumentationsX MCP config. | `docs/CLAUDE_CODE_SETUP_PATH.md` |

## Operator Commands

- `uv run python scripts/check_host_setup_probe.py --live --format json`
- `uv run python scripts/check_p0_host_run_preflight.py`
- `uv run python scripts/export_manual_host_acceptance_packet.py --host '<host>' --output /tmp/albu-host-<host>.md`
- `uv run python scripts/record_host_manual_run.py --host '<host>' --status passed --date YYYY-MM-DD --evidence '<redacted reviewer-observed evidence>'`
- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json`

## Recorder

`scripts/record_host_manual_run.py` is the only P0 evidence writer.

## Source Docs

- `docs/HOST_SETUP_PROBE.md`
- `docs/HOST_EVIDENCE_RUNNER.md`
- `docs/P0_EVIDENCE_RECORDER.md`
- `docs/P0_HOST_EVIDENCE_RECOVERY.md`
- `docs/HOST_MANUAL_RUNS.json`
