# V1 RC Cutover Gate

Package: `albumentationsx-mcp==1.15.0`
Release tag: `vX.Y.Z-rc.1`
Required hosts: `Codex, Claude Code`
Gate status: `blocked`
Cutover allowed: `false`
RC decision: `hold_rc`
Blocked reason: `p0_host_evidence_missing_or_blocked`

## Gate Policy

The RC cutover gate refuses release while any P0 real-host evidence gate is not passed.

## P0 Summary

- required_gate_count: `4`
- recorded_gate_count: `0`
- missing_gate_count: `4`
- blocked_gate_count: `0`

## Failed Gates

| Host | Gate | Record Status | Date | Evidence |
| --- | --- | --- | --- | --- |
| Codex | `first_10_minutes_replay` | `missing` | `not_recorded` | No reviewer-observed real UI evidence recorded. |
| Codex | `manual_host_ui` | `missing` | `not_recorded` | No reviewer-observed real UI evidence recorded. |
| Claude Code | `first_10_minutes_replay` | `missing` | `not_recorded` | No reviewer-observed real UI evidence recorded. |
| Claude Code | `manual_host_ui` | `missing` | `not_recorded` | No reviewer-observed real UI evidence recorded. |

## Preflight Commands

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
- `uv run python scripts/check_release_readiness.py`
- `uv build`

## Publish Commands

- none

## Blocked Publish Commands

- `git tag vX.Y.Z-rc.1`
- `git push origin vX.Y.Z-rc.1`
- `gh release create vX.Y.Z-rc.1 --prerelease --generate-notes`

## Source Docs

- `docs/P0_HOST_EVIDENCE_LEDGER.md`
- `docs/P0_EVIDENCE_REGENERATION_PACK.md`
- `docs/V1_RC_READINESS.md`
- `docs/V1_RC_AUTOMATION_PACK.md`

## Next Action

Do not tag or publish the RC; complete P0 real-host evidence and rerun this gate with --require-open.
