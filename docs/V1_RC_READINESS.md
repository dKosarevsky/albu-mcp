# V1 RC Readiness Report

Package: `albumentationsx-mcp==1.15.0`
Required RC hosts: `Codex, Claude Code`
RC decision: `hold_rc`
RC release candidate allowed: `false`
Stable v1 allowed: `false`

## Policy

RC requires real P0 host evidence; stable v1 requires every supported host gate.

## RC Blockers

| Host | Priority | Gate | Evidence Status | Next Action |
| --- | --- | --- | --- | --- |
| Codex | `p0` | `first_10_minutes_replay` | `missing` | `run_first_10_minutes_replay` |
| Codex | `p0` | `manual_host_ui` | `missing` | `run_manual_host_ui` |
| Claude Code | `p0` | `first_10_minutes_replay` | `missing` | `run_first_10_minutes_replay` |
| Claude Code | `p0` | `manual_host_ui` | `missing` | `run_manual_host_ui` |

## Promotion Rule

Stable v1 requires all supported hosts to pass.

## Next Checks

- `uv run python scripts/export_real_host_evidence_execution_pack.py --output docs/REAL_HOST_EVIDENCE_EXECUTION.md`
- `uv run python scripts/export_host_ux_hardening_loop.py --output docs/HOST_UX_HARDENING_LOOP.md`
- `uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md`
- `uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md`
- `uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md`
- `uv run python scripts/check_release_readiness.py`
