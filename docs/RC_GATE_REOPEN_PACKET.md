# RC Gate Reopen Packet

Package: `albumentationsx-mcp==1.15.0`
Release tag: `vX.Y.Z-rc.1`
Reopen status: `blocked_until_p0_and_beta_evidence`
Cutover allowed: `false`
Publish allowed: `false`
Dry run allowed: `true`
RC decision: `hold_rc`

## Reopen Policy

Do not create RC tags, GitHub Releases, PyPI uploads, or public rollout announcements until this packet has reopen_status ready_for_rc_cutover and the hard gate exits 0 with --require-open.

## Summary

- p0_blocked_gate_count: `2`
- p0_passed_gate_count: `2`
- beta_record_count: `0`
- beta_missing_workflow_count: `3`
- promoted_backlog_item_count: `0`
- blocked_publish_command_count: `3`

## Reopen Blockers

- `p0_host_evidence_blocked`
- `beta_validation_records_missing`
- `p0_host_evidence_missing_or_blocked`

## Open Criteria

- Every Codex and Claude Code P0 host evidence gate has record_status `passed`.
- Every beta validation workflow has at least one privacy-safe real attempt recorded.
- `uv run python scripts/check_release_readiness.py` exits 0 after regenerating reports.
- `uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json` exits 0.

## Reopen Sequence

1. Run docs/P0_HOST_EVIDENCE_RECOVERY.md and replace blocked P0 records only with real host evidence.
2. Run docs/BETA_VALIDATION_RECORDING_PACK.md and record privacy-safe real beta attempts.
3. Regenerate P0, beta, RC, and product-depth generated docs.
4. Run release readiness, full tests, type checks, formatting, and local build.
5. Run the hard RC cutover gate with --require-open.
6. Create RC tag and GitHub prerelease only after the hard gate opens.

## Safe Commands

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

## Source Docs

- `docs/P0_HOST_EVIDENCE_RECOVERY.md`
- `docs/BETA_VALIDATION_RECORDING_PACK.md`
- `docs/BETA_TO_BACKLOG_TRIAGE.md`
- `docs/RC_DRY_RUN.md`
- `docs/V1_RC_CUTOVER_GATE.md`
