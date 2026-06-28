# V1 RC Rehearsal Plan

Package: `albumentationsx-mcp==1.15.0`
Release tag: `vX.Y.Z-rc.1`
Rehearsal status: `preflight_only`
RC cutover allowed: `false`
Dry run allowed: `true`
Publish allowed: `false`

## Operator Policy

Do not create tags, GitHub Releases, or PyPI uploads during rehearsal.

## P0 Summary

- required_gate_count: `4`
- recorded_gate_count: `0`
- missing_gate_count: `0`
- blocked_gate_count: `4`

## Dry-Run Commands

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

## Stop Conditions

- Any P0 host evidence gate is missing or blocked.
- The worktree is dirty after regenerating release reports.
- Any local verification command fails.

## Source Docs

- `docs/V1_RC_CUTOVER_GATE.md`
- `docs/V1_RC_AUTOMATION_PACK.md`
- `docs/DISTRIBUTION_READINESS_PACK.md`
- `docs/P0_EVIDENCE_STATUS.md`
