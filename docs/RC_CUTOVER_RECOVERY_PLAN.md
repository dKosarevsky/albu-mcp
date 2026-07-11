# RC Cutover Recovery Plan

Package: `albumentationsx-mcp==1.16.0`
Release tag: `vX.Y.Z-rc.1`
Recovery status: `blocked_by_p0_evidence`
RC cutover allowed: `false`
Publish allowed: `false`
Safe preflight allowed: `true`
Distribution status: `blocked_until_rc_cutover`

## Operator Policy

Do not tag, create a GitHub Release, or publish to PyPI while recovery_status is blocked.

## P0 Summary

- required_gate_count: `4`
- recorded_gate_count: `2`
- missing_gate_count: `0`
- blocked_gate_count: `2`

## Recovery Steps

- Run the safe preflight commands to confirm the codebase is still releasable.
- Resolve every P0 lane in docs/P0_HOST_UNBLOCK_PACK.md with real host evidence.
- Regenerate P0, RC, and distribution reports after evidence changes.
- Rerun the hard RC cutover gate with --require-open before any tag or publish command.

## Failed Gates

- Claude Code / `first_10_minutes_replay`: `blocked` on `2026-06-28`
- Claude Code / `manual_host_ui`: `blocked` on `2026-06-28`

## Safe Preflight Commands

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

## Reopen Criteria

- Every P0 host gate has record_status `passed`.
- `uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json` exits 0.
- Distribution rollout remains unpublished until the RC tag and package are visible.

## Source Docs

- `docs/V1_RC_CUTOVER_GATE.md`
- `docs/V1_RC_REHEARSAL_PLAN.md`
- `docs/DISTRIBUTION_ROLLOUT_PACKET.md`
- `docs/P0_HOST_UNBLOCK_PACK.md`
