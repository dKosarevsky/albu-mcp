# V1 Evidence Operator Packet

Packet status: `manual_evidence_required`
RC publish allowed: `false`
Required hosts: `Codex, Claude Code`

## Operator Policy

Do not create an RC tag until all P0 host gates are passed in real host UI.

## Summary

- required_gate_count: `4`
- recorded_gate_count: `0`
- missing_gate_count: `0`
- blocked_gate_count: `4`

## Operator Lanes

## Codex

Host prompt:

> List AlbumentationsX MCP tools, call run_host_smoke_check, complete the First 10 Minutes workflow, and record only reviewer-observed real host UI evidence.

Record commands:

- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed --date YYYY-MM-DD --evidence '<redacted evidence>' --artifact docs/assets/demo/demo_report.md`
- `uv run python scripts/record_host_manual_run.py --host Codex --status passed --date YYYY-MM-DD --evidence '<redacted evidence>'`

Gate statuses:

- `first_10_minutes_replay`: `blocked`
- `manual_host_ui`: `blocked`

## Claude Code

Host prompt:

> List AlbumentationsX MCP tools, call run_host_smoke_check, complete the First 10 Minutes workflow, and record only reviewer-observed real host UI evidence.

Record commands:

- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence '<redacted evidence>' --artifact docs/assets/demo/demo_report.md`
- `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence '<redacted evidence>'`

Gate statuses:

- `first_10_minutes_replay`: `blocked`
- `manual_host_ui`: `blocked`

## Post-Recording Commands

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md`
- `uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md`
- `uv run python scripts/export_v1_evidence_operator_packet.py --output docs/V1_EVIDENCE_OPERATOR_PACKET.md`
- `uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md`
- `uv run python scripts/export_v1_rc_automation_pack.py --output docs/V1_RC_AUTOMATION_PACK.md`
- `uv run python scripts/check_release_readiness.py`

## Source Docs

- `docs/P0_HOST_EVIDENCE_LEDGER.md`
- `docs/V1_RC_AUTOMATION_PACK.md`
- `docs/HOST_MANUAL_RUNS.json`
