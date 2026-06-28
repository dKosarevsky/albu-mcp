# Host Onboarding Depth Plan

Plan status: `blocked_until_depth_gate_opens`
Implementation allowed: `false`
Product area: `host_onboarding`
Triage bucket: `host_setup_gap`

## Depth Policy

Do not implement host-onboarding depth work until RC and beta gates open.

## Candidate

- Candidate: Host-specific setup probes and clearer blocked evidence capture.
- Success signal: A beta user can recover from setup failure without maintainer intervention.

## Blocked Reasons

- `rc_cutover_blocked`
- `beta_validation_incomplete`

## Implementation Slices

| Deliverable | Status | Outcome | Test Focus |
| --- | --- | --- | --- |
| `host_setup_probe` | `planned_after_gate` | Detect missing CLI, stale MCP tool discovery, and invalid roots before the first preview. | Parameterized host setup diagnostics for Codex, Claude Code, Cursor, and Claude Desktop. |
| `approval_troubleshooting` | `planned_after_gate` | Explain host tool-approval cancellation without asking users to inspect private logs. | Blocked Codex tool-call evidence maps to a concrete recovery step. |
| `blocked_evidence_capture` | `planned_after_gate` | Convert repeated setup failures into structured blocked evidence and next actions. | Record commands preserve privacy and never convert blocked evidence into passed evidence. |

## Failure Classes To Cover

- `tools_not_visible`
- `stale_tool_cache`
- `path_policy_rejected`
- `artifact_root_unwritable`
- `uvx_startup_failed`

## Active P0 Blockers

- Codex / `first_10_minutes_replay`: `codex_tool_call_cancelled`
- Codex / `manual_host_ui`: `codex_tool_call_cancelled`
- Claude Code / `first_10_minutes_replay`: `claude_cli_missing`
- Claude Code / `manual_host_ui`: `claude_cli_missing`

## Source Docs

- `docs/PRODUCT_DEPTH_SELECTION.md`
- `docs/HOST_FAILURE_COOKBOOK.md`
- `docs/P0_HOST_UNBLOCK_PACK.md`
