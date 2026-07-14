# V1 RC Cutover Checklist

Package: `albumentationsx-mcp==1.19.0`
Required hosts: `Codex, Claude Code`
RC decision: `hold_rc`
Release candidate allowed: `false`
Cutover status: `blocked`

## Hard Gates

- P0 real host evidence passed for Codex and Claude Code.
- Generated P0 evidence status and v1 RC release packet are current.
- Local release readiness, type checks, lint, tests, and build pass.
- CI passes on the supported Python matrix.

## No-Go Rules

- Do not create or push an RC tag while cutover_status is blocked.
- Do not use synthetic host evidence to satisfy P0 gates.
- Do not publish a GitHub Release or PyPI build before the RC tag exists.

## Ready Commands

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
- `uv run python scripts/check_release_readiness.py`
- `uv build`
- `git tag vX.Y.Z-rc.1`
- `git push origin vX.Y.Z-rc.1`
- `gh release create vX.Y.Z-rc.1 --prerelease --generate-notes`

## Source Reports

- `docs/V1_RC_READINESS.md`
- `docs/P0_EVIDENCE_STATUS.md`
- `docs/P0_HOST_EXECUTION_SPRINT.md`
- `docs/P0_BLOCKER_TRIAGE.md`
