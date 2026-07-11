# P0 Host Execution Sprint

Target hosts: `Codex, Claude Code`
Execution status: `manual_evidence_required`

## Non-Fabrication Policy

Never mark a host passed without reviewer-observed real UI evidence.

## Source Docs

- `docs/P0_HOST_RUNBOOK.md`
- `docs/P0_EVIDENCE_RECORDER.md`
- `docs/P0_EVIDENCE_STATUS.md`
- `docs/P0_BLOCKER_TRIAGE.md`

## Gate Matrix

| Host | Gate | Evidence Status | Next Action | Operator Packet |
| --- | --- | --- | --- | --- |
| Claude Code | `first_10_minutes_replay` | `blocked` | `triage_blocker` | `uv run python scripts/export_manual_host_acceptance_packet.py --host 'Claude Code' --output /tmp/albu-host-claude-code.md` |
| Claude Code | `manual_host_ui` | `blocked` | `triage_blocker` | `uv run python scripts/export_manual_host_acceptance_packet.py --host 'Claude Code' --output /tmp/albu-host-claude-code.md` |

## Stop Conditions

- Do not tag v1 RC while any P0 gate is missing or blocked.
- Do not convert pending evidence into passed evidence without a real host UI run.
- Record blocked evidence at the first failing gate and use docs/P0_BLOCKER_TRIAGE.md.

## After Real UI Runs

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md`
- `uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md`
- `uv run python scripts/export_v1_rc_release_packet.py --output docs/V1_RC_RELEASE_PACKET.md`
- `uv run python scripts/check_release_readiness.py`
