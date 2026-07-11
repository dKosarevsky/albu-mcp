# RC Dry Run

Package: `albumentationsx-mcp==1.15.0`
Release tag: `vX.Y.Z-rc.1`
Dry-run status: `preflight_only_blocked_publish`
Gate status: `blocked`
Blocked reason: `p0_host_evidence_missing_or_blocked`
Dry run allowed: `true`
Publish allowed: `false`
RC cutover allowed: `false`
Distribution status: `blocked_until_rc_cutover`
Stabilization status: `blocked_until_trust_gates_pass`

## Operator Policy

Run safe checks and local builds only. Do not create tags, GitHub Releases, public announcements, or PyPI uploads from this dry run.

## P0 Summary

- required_gate_count: `4`
- recorded_gate_count: `2`
- missing_gate_count: `0`
- blocked_gate_count: `2`

## Safe Dry-Run Commands

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
- `uv run python scripts/check_release_readiness.py`
- `uv build`
- `uv run python scripts/check_v1_rc_cutover_gate.py --format json`
- `uv run python scripts/export_rc_dry_run.py --output docs/RC_DRY_RUN.md`

## Blocked Publish Commands

- `git tag vX.Y.Z-rc.1`
- `git push origin vX.Y.Z-rc.1`
- `gh release create vX.Y.Z-rc.1 --prerelease --generate-notes`

## Blocked Distribution Actions

- Complete P0 host evidence and RC cutover before public rollout.
- Keep announcement copy prepared but unpublished.
- Regenerate this packet after RC distribution readiness changes.

## Success Criteria

- Every safe dry-run command exits 0.
- uv build creates local artifacts only; no upload is attempted.
- The hard RC cutover gate remains blocked unless every P0 host gate is passed.
- Regenerated RC docs match committed generated-doc checks.

## Reopen Criteria

- Every P0 host gate has record_status `passed`.
- `uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json` exits 0.
- Distribution rollout remains unpublished until the RC tag and package are visible.

## Source Docs

- `docs/V1_RC_REHEARSAL_PLAN.md`
- `docs/RC_CUTOVER_RECOVERY_PLAN.md`
- `docs/DISTRIBUTION_ROLLOUT_PACKET.md`
- `docs/V1_STABILIZATION_PLAN.md`
- `docs/V1_RC_CUTOVER_GATE.md`
