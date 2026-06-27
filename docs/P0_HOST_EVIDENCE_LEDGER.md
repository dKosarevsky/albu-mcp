# P0 Host Evidence Ledger

Records path: `docs/HOST_MANUAL_RUNS.json`
Target hosts: `Codex, Claude Code`
Ledger status: `manual_evidence_required`

## Non-Fabrication Policy

Only docs/HOST_MANUAL_RUNS.json can satisfy a P0 gate.

## Summary

- required_gate_count: `4`
- recorded_gate_count: `0`
- missing_gate_count: `4`
- blocked_gate_count: `0`

## Gate Records

| Host | Gate | Record Status | Date | Evidence | Record Command |
| --- | --- | --- | --- | --- | --- |
| Codex | `first_10_minutes_replay` | `missing` | `not_recorded` | No reviewer-observed real UI evidence recorded. | `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed --date YYYY-MM-DD --evidence '<redacted evidence>' --artifact docs/assets/demo/demo_report.md` |
| Codex | `manual_host_ui` | `missing` | `not_recorded` | No reviewer-observed real UI evidence recorded. | `uv run python scripts/record_host_manual_run.py --host Codex --status passed --date YYYY-MM-DD --evidence '<redacted evidence>'` |
| Claude Code | `first_10_minutes_replay` | `missing` | `not_recorded` | No reviewer-observed real UI evidence recorded. | `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence '<redacted evidence>' --artifact docs/assets/demo/demo_report.md` |
| Claude Code | `manual_host_ui` | `missing` | `not_recorded` | No reviewer-observed real UI evidence recorded. | `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence '<redacted evidence>'` |

## After Recording

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md`
- `uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md`
- `uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md`
- `uv run python scripts/check_release_readiness.py`
