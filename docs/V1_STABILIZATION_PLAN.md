# V1 Stabilization Plan

Package: `albumentationsx-mcp==1.17.1`
Stabilization status: `blocked_until_trust_gates_pass`
Ready for v1: `false`
Stable v1 allowed: `false`
Manual gate count: `5`
Cutover status: `blocked_by_p0_evidence`

## Feature Freeze Policy

Keep v1 scope frozen to release reliability, host evidence, beta validation, and documentation corrections.

## V1 Scope

- Stable MCP server packaging and server.json metadata.
- Privacy-safe local image and artifact workflows.
- Host evidence gates for Codex and Claude Code before RC publication.
- Beta workflow intake for robustness variants, noisy preview tuning, and dataset health.
- Release and distribution docs that are generated from committed evidence.

## Exit Criteria

- P0 host evidence is passed for required RC hosts.
- RC cutover gate opens with --require-open.
- At least one privacy-safe beta validation attempt exists for each beta workflow.
- Release readiness, tests, lint, type checks, build, and MCP smoke pass in CI.
- PyPI, GitHub Release, MCP Registry, and directory visibility pass after RC publication.

## Non-Goals

- Do not reduce the supported host set only to make the gate pass.
- Do not mark generated MCP smoke output as real host UI evidence.
- Do not publish a stable v1 while host_blocker_count is greater than zero.

## Post-V1 Backlog

| Item | Status | Candidate |
| --- | --- | --- |
| `host_onboarding` | `blocked_until_depth_gate_opens` | Host-specific setup probes and clearer blocked evidence capture. |
| `review_agent_v3` | `waiting_for_beta_signal` | Feedback-to-adjustment improvements after repeated noisy-preview beta findings. |
| `dataset_quality_depth` | `waiting_for_beta_signal` | Deeper annotation, class-balance, and duplicate checks after beta validation. |

## Source Docs

- `docs/V1_DECISION_REPORT.md`
- `docs/V1_TRUST_GATES.md`
- `docs/V1_GROWTH_CUTOVER_REPORT.md`
- `docs/PRODUCT_DEPTH_SELECTION.md`
