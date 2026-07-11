# P0 Blocker Triage Matrix

## Source Docs

- `docs/P0_EVIDENCE_STATUS.md`
- `docs/HOST_FAILURE_COOKBOOK.md`
- `docs/HOST_UX_HARDENING_LOOP.md`

## Triage Matrix

| Host | Gate | Evidence Status | Triage Action | Entrypoints |
| --- | --- | --- | --- | --- |
| Claude Code | `first_10_minutes_replay` | `blocked` | `triage_blocker` | `docs/P0_HOST_RUNBOOK.md`, `docs/P0_EVIDENCE_RECORDER.md`, `docs/HOST_FAILURE_COOKBOOK.md` |
| Claude Code | `manual_host_ui` | `blocked` | `triage_blocker` | `docs/P0_HOST_RUNBOOK.md`, `docs/P0_EVIDENCE_RECORDER.md`, `docs/HOST_FAILURE_COOKBOOK.md` |

## Failure Classes

- `tools_not_visible`
- `stale_tool_cache`
- `path_policy_rejected`
- `artifact_root_unwritable`
- `uvx_startup_failed`

## Escalation Rule

Convert repeated blocked evidence into a regression test before changing product behavior.
