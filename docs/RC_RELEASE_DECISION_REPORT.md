# RC Release Decision Report

Decision: `no_go`
Release tag: `v1.15.0-rc.1`
Cutover allowed: `false`
Publish allowed: `false`

## Release Policy

Do not create tags, GitHub Releases, PyPI uploads, or public announcements.

## Blocked Reasons

- `p0_host_evidence_missing_or_blocked`
- `beta_validation_records_missing`

## Completed Enablers

- `package_evidence_cli`
- `package_beta_triage_cli`
- `preview_gated_policy_assistant_tool`

## Safe Commands

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
- `uv run python scripts/check_release_readiness.py`
- `uv build`

## Blocked Publish Commands

- `git tag v1.15.0-rc.1`
- `git push origin v1.15.0-rc.1`
- `gh release create v1.15.0-rc.1 --prerelease --generate-notes`

## Source Docs

- `docs/V1_RC_CUTOVER_GATE.md`
- `docs/BETA_VALIDATION_STATUS.md`
- `docs/HOST_MANUAL_RUNS.json`
