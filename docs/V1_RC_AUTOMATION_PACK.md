# V1 RC Automation Pack

Package: `albumentationsx-mcp==1.15.0`
Required hosts: `Codex, Claude Code`
RC decision: `hold_rc`
Release candidate allowed: `false`
Automation status: `blocked`

## Operator Warnings

- Do not run publish commands while automation_status is blocked.
- Do not create an RC tag before P0 real host evidence is recorded.
- Run preflight commands from a clean worktree after regenerating release reports.

## Preflight Commands

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
- `uv run python scripts/check_release_readiness.py`
- `uv build`

## Publish Commands

- `git tag vX.Y.Z-rc.1`
- `git push origin vX.Y.Z-rc.1`
- `gh release create vX.Y.Z-rc.1 --prerelease --generate-notes`

## Source Docs

- `docs/V1_RC_CUTOVER_CHECKLIST.md`
- `docs/V1_RC_RELEASE_PACKET.md`
- `docs/P0_HOST_EVIDENCE_LEDGER.md`
