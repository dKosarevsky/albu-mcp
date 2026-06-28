# P0 Host Run Session

Session status: `manual_evidence_required`
Required hosts: `Codex, Claude Code`

## Non-Fabrication Policy

Record only reviewer-observed real host UI evidence.

## Summary

- required_gate_count: `4`
- recorded_gate_count: `0`
- missing_gate_count: `0`
- blocked_gate_count: `4`

## Host Sessions

## Codex Session

Session status: `blocked`

Host prompt:

> List AlbumentationsX MCP tools, call run_host_smoke_check, complete the First 10 Minutes workflow, and record only reviewer-observed real host UI evidence.

Run checklist:

- Start the MCP host with the published or local server command.
- List AlbumentationsX MCP tools/resources in the real host UI.
- Call run_host_smoke_check and inspect preview_ready.
- Complete docs/FIRST_10_MINUTES.md in the same host UI.
- Record only redacted, reviewer-observed evidence after the run.

Record commands:

- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed --date YYYY-MM-DD --evidence '<redacted evidence>' --artifact docs/assets/demo/demo_report.md`
- `uv run python scripts/record_host_manual_run.py --host Codex --status passed --date YYYY-MM-DD --evidence '<redacted evidence>'`

Evidence candidate templates:

`manual_host_ui`:

```json
{
  "host": "Codex",
  "status": "passed",
  "date": "YYYY-MM-DD",
  "evidence": "Redacted reviewer-observed Codex host UI evidence summary."
}
```

`first_10_minutes_replay`:

```json
{
  "host": "Codex",
  "status": "passed",
  "date": "YYYY-MM-DD",
  "evidence": "Redacted reviewer-observed Codex first-10-minutes replay summary.",
  "artifacts": [
    "docs/assets/demo/demo_report.md"
  ]
}
```


Gate statuses:

- `first_10_minutes_replay`: `blocked`
- `manual_host_ui`: `blocked`

## Claude Code Session

Session status: `blocked`

Host prompt:

> List AlbumentationsX MCP tools, call run_host_smoke_check, complete the First 10 Minutes workflow, and record only reviewer-observed real host UI evidence.

Run checklist:

- Start the MCP host with the published or local server command.
- List AlbumentationsX MCP tools/resources in the real host UI.
- Call run_host_smoke_check and inspect preview_ready.
- Complete docs/FIRST_10_MINUTES.md in the same host UI.
- Record only redacted, reviewer-observed evidence after the run.

Record commands:

- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence '<redacted evidence>' --artifact docs/assets/demo/demo_report.md`
- `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence '<redacted evidence>'`

Evidence candidate templates:

`manual_host_ui`:

```json
{
  "host": "Claude Code",
  "status": "passed",
  "date": "YYYY-MM-DD",
  "evidence": "Redacted reviewer-observed Claude Code host UI evidence summary."
}
```

`first_10_minutes_replay`:

```json
{
  "host": "Claude Code",
  "status": "passed",
  "date": "YYYY-MM-DD",
  "evidence": "Redacted reviewer-observed Claude Code first-10-minutes replay summary.",
  "artifacts": [
    "docs/assets/demo/demo_report.md"
  ]
}
```


Gate statuses:

- `first_10_minutes_replay`: `blocked`
- `manual_host_ui`: `blocked`

## Post-Session Commands

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md`
- `uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md`
- `uv run python scripts/export_v1_evidence_operator_packet.py --output docs/V1_EVIDENCE_OPERATOR_PACKET.md`
- `uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md`
- `uv run python scripts/export_v1_rc_automation_pack.py --output docs/V1_RC_AUTOMATION_PACK.md`
- `uv run python scripts/check_release_readiness.py`

## Source Docs

- `docs/V1_EVIDENCE_OPERATOR_PACKET.md`
- `docs/P0_HOST_EVIDENCE_LEDGER.md`
- `docs/FIRST_10_MINUTES.md`
- `docs/HOST_MANUAL_RUNS.json`
