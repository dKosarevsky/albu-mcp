# Product Depth Gate

Gate status: `blocked_by_rc_and_beta_signal`
Product depth allowed: `false`
RC cutover allowed: `false`
Beta validation status: `manual_beta_required`
Backlog status: `waiting_for_beta_signal`

## Prioritization Rule

Do not promote depth work above P0 host evidence until RC gates pass.

## Blocked Reasons

- `rc_cutover_blocked`
- `beta_validation_incomplete`

## Summary

- backlog_item_count: `5`
- beta_record_count: `0`
- beta_covered_workflow_count: `0`
- required_beta_workflow_count: `3`

## Candidate Items

| Product Area | Priority | Candidate | Success Signal |
| --- | --- | --- | --- |
| `host_onboarding` | `p1_after_p0` | Host-specific setup probes and clearer blocked evidence capture. | A beta user can recover from setup failure without maintainer intervention. |
| `preview_review_agent` | `p1_after_p0` | Feedback-to-adjustment planning that better handles noisy or unreadable previews. | Repeated noisy-preview feedback maps to safer candidate adjustments. |
| `dataset_quality` | `p1_after_p0` | Deeper dataset health findings for annotations, class balance, and duplicate handling. | Dataset issues are caught before preview rendering in beta workflows. |
| `host_docs` | `p2_after_beta` | Short host-specific cards for Codex, Claude Code, Cursor, and Claude Desktop. | Users can start the first preview without reading long-form docs. |
| `cv_workflow_templates` | `p2_after_beta` | More task-specific workflow templates for robustness, OCR, detection, and segmentation. | Beta users select a workflow template without custom prompting. |

## Source Docs

- `docs/PRODUCT_DEPTH_BACKLOG.md`
- `docs/BETA_VALIDATION_STATUS.md`
- `docs/V1_RC_CUTOVER_GATE.md`

## Next Actions

- Complete P0 real-host evidence and open the RC cutover gate before product-depth work.
- Record one privacy-safe real beta attempt for each beta workflow.
