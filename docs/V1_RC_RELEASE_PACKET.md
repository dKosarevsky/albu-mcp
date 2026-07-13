# V1 RC Release Packet

Package: `albumentationsx-mcp==1.17.1`
Required hosts: `Codex, Claude Code`
RC decision: `hold_rc`
Release candidate allowed: `false`

## P0 Summary

- host_count: `2`
- passed_gate_count: `2`
- required_gate_count: `4`
- blocked_gate_count: `2`
- missing_gate_count: `0`

## Blocked Release Steps

- Do not tag v1 RC until P0 real host evidence passes.
- Run docs/P0_HOST_RUNBOOK.md for Codex and Claude Code.
- Record evidence through docs/P0_EVIDENCE_RECORDER.md.
- Regenerate docs/P0_EVIDENCE_STATUS.md and docs/V1_RC_READINESS.md.

## Ready Release Steps

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
- `uv run python scripts/check_release_readiness.py`
- `uv build`
- `git tag vX.Y.Z-rc.1`

## Source Reports

- `docs/V1_RC_READINESS.md`
- `docs/P0_EVIDENCE_STATUS.md`
