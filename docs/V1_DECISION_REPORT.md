# V1 Decision Report

Package: `albumentationsx-mcp==1.15.0`
Server version: `1.15.0`
Ready for v1: `false`
Decision: `hold_v1`
Release candidate allowed: `false`
Host blocker count: `6`

## Decision Policy

Do not cut v1 from synthetic or generated host evidence.

## Blocking Codes

- `manual_host_ui_pending`
- `first_10_minutes_replay_pending`

## Required Before V1

- Run host evidence sprint queue and record real host UI evidence.
- Record First 10 Minutes replay artifacts for every supported host.
- Record manual Host UI evidence for every supported host.
- Regenerate V1 Launch Report and V1 Decision Report after evidence changes.

## Non-Goals

- Do not reduce the supported host set only to make the gate pass.
- Do not mark generated MCP smoke output as real host UI evidence.
- Do not publish a stable v1 while host_blocker_count is greater than zero.

## Next Decision Checks

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/check_first_10_minutes_replay.py`
- `uv run python scripts/check_manual_host_acceptance.py`
- `uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md`
- `uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md`
- `uv run python scripts/check_release_readiness.py`
