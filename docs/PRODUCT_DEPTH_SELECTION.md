# Product Depth Selection

Selection status: `blocked_until_depth_gate_opens`
Implementation allowed: `false`

## Decision Policy

Select one P1 depth item only after RC and beta validation gates open.

## Blocked Reasons

- `rc_cutover_blocked`
- `beta_validation_incomplete`

## Recommended Candidate

- Product area: `host_onboarding`
- Triage bucket: `host_setup_gap`
- Priority: `p1_after_p0`
- Candidate: Host-specific setup probes and clearer blocked evidence capture.
- Success signal: A beta user can recover from setup failure without maintainer intervention.

## Selection Rationale

- Start with the first P1 candidate because host setup failure blocks every beta workflow.
- Keep review-agent and dataset-depth changes behind real beta validation signal.
- Do not start parallel product-depth work until the selected item has tests and docs.

## Next Actions

- Complete P0 real-host evidence and beta validation before implementation.
- Keep this selection as a planning artifact, not an implementation approval.
- Rebuild this document after evidence and beta records change.

## Source Docs

- `docs/PRODUCT_DEPTH_GATE.md`
- `docs/PRODUCT_DEPTH_BACKLOG.md`
- `docs/BETA_VALIDATION_STATUS.md`
- `docs/V1_RC_CUTOVER_GATE.md`
