# RC Evidence Reopen Flow

Flow status: `blocked_until_p0_and_beta_evidence`
Decision: `hold_rc`
Cutover allowed: `false`
Publish allowed: `false`
Hard gate command: `uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json`

## Operator Policy

No tag, release, upload, or public announcement is allowed while any evidence gate is blocked.

## Gates

| Gate | Status | Required Before |
| --- | --- | --- |
| `p0_host_evidence` | `blocked` | `rc_tag` |
| `beta_validation` | `missing` | `rc_tag` |
| `release_readiness` | `ready` | `rc_tag` |
| `hard_rc_gate` | `blocked` | `publish` |

## Safe Commands

- `uv run python scripts/check_host_setup_probe.py --live --format json`
- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/validate_beta_validation_records.py`
- `uv run python scripts/check_release_readiness.py`
- `uv run python scripts/check_v1_rc_cutover_gate.py --format json`

## Blocked Publish Commands

- `git tag vX.Y.Z-rc.1`
- `git push origin vX.Y.Z-rc.1`
- `gh release create vX.Y.Z-rc.1 --prerelease --generate-notes`

## Source Docs

- `docs/RC_GATE_REOPEN_PACKET.md`
- `docs/V1_RC_CUTOVER_GATE.md`
- `docs/P0_HOST_EVIDENCE_RECOVERY.md`
- `docs/BETA_VALIDATION_STATUS.md`
