# RC Host Evidence Ops

Package: `albumentationsx-mcp==1.15.0`
Records path: `docs/HOST_MANUAL_RUNS.json`
Required hosts: `Codex, Claude Code`
Ops status: `blocked_until_real_host_runs`
RC cutover allowed: `false`

## Non-Fabrication Policy

Do not record passed evidence without a real host UI run.

## P0 Summary

- required_gate_count: `4`
- recorded_gate_count: `0`
- missing_gate_count: `4`
- blocked_gate_count: `0`

## Gate Records

| Host | Gate | Record Status | Date | Evidence |
| --- | --- | --- | --- | --- |
| Codex | `first_10_minutes_replay` | `missing` | `not_recorded` | No reviewer-observed real UI evidence recorded. |
| Codex | `manual_host_ui` | `missing` | `not_recorded` | No reviewer-observed real UI evidence recorded. |
| Claude Code | `first_10_minutes_replay` | `missing` | `not_recorded` | No reviewer-observed real UI evidence recorded. |
| Claude Code | `manual_host_ui` | `missing` | `not_recorded` | No reviewer-observed real UI evidence recorded. |

## Run Commands

- `uv run python scripts/check_p0_host_run_preflight.py`
- `uv run python scripts/export_p0_host_run_session.py --output docs/P0_HOST_RUN_SESSION.md`
- `uv run python scripts/verify_host_evidence_import.py --input /path/to/host-evidence-candidate.json`
- `uv run python scripts/validate_host_manual_runs.py`

## After Recording Commands

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md`
- `uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md`
- `uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md`
- `uv run python scripts/export_v1_rc_release_packet.py --output docs/V1_RC_RELEASE_PACKET.md`
- `uv run python scripts/export_v1_rc_cutover_checklist.py --output docs/V1_RC_CUTOVER_CHECKLIST.md`
- `uv run python scripts/export_v1_rc_automation_pack.py --output docs/V1_RC_AUTOMATION_PACK.md`
- `uv run python scripts/export_v1_growth_cutover_report.py --output docs/V1_GROWTH_CUTOVER_REPORT.md`
- `uv run python scripts/check_release_readiness.py`

## RC Gate Commands

- `uv run python scripts/check_v1_rc_cutover_gate.py --output docs/V1_RC_CUTOVER_GATE.md`
- `uv run python scripts/check_v1_rc_cutover_gate.py --require-open`

## Blocked Publish Commands

- `git tag vX.Y.Z-rc.1`
- `git push origin vX.Y.Z-rc.1`
- `gh release create vX.Y.Z-rc.1 --prerelease --generate-notes`

## Source Docs

- `docs/P0_HOST_RUN_SESSION.md`
- `docs/P0_HOST_RUN_PREFLIGHT.md`
- `docs/P0_EVIDENCE_IMPORT_GUIDE.md`
- `docs/P0_EVIDENCE_REGENERATION_PACK.md`
- `docs/V1_RC_CUTOVER_GATE.md`

## Next Action

Run real Codex and Claude Code host UI sessions, verify evidence candidates, and record only observed results.
