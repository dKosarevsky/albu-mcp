# Beta-to-Backlog Triage

Triage status: `blocked_until_beta_signal`
Product depth allowed: `false`
Beta validation status: `manual_beta_required`

## Triage Policy

Promote product-depth work only when repeated privacy-safe beta records support a backlog bucket and the product-depth gate is open.

## Summary

- record_count: `0`
- workflow_count: `3`
- covered_workflow_count: `0`
- backlog_item_count: `5`
- promoted_backlog_item_count: `0`

## Blocked Reasons

- `rc_cutover_blocked`
- `beta_validation_incomplete`

## Triage Lanes

| Bucket | Signal Count | Product Area | Recommendation Status | Candidate |
| --- | --- | --- | --- | --- |
| `host_setup_gap` | `0` | `host_onboarding` | `blocked_no_beta_signal` | Host-specific setup probes and clearer blocked evidence capture. |
| `review_agent_v3_gap` | `0` | `preview_review_agent` | `blocked_no_beta_signal` | Feedback-to-adjustment planning that better handles noisy or unreadable previews. |
| `dataset_quality_gap` | `0` | `dataset_quality` | `blocked_no_beta_signal` | Deeper dataset health findings for annotations, class balance, and duplicate handling. |
| `docs_gap` | `0` | `host_docs` | `blocked_no_beta_signal` | Short host-specific cards for Codex, Claude Code, Cursor, and Claude Desktop. |
| `workflow_fit_gap` | `0` | `cv_workflow_templates` | `blocked_no_beta_signal` | More task-specific workflow templates for robustness, OCR, detection, and segmentation. |

## Next Actions

- Collect one privacy-safe beta validation record for each beta workflow.
- Regenerate beta validation status and this triage report after recording attempts.
- Promote only repeated or high-confidence beta findings into implementation plans.

## Source Docs

- `docs/BETA_VALIDATION_STATUS.md`
- `docs/BETA_VALIDATION_RECORDING_PACK.md`
- `docs/PRODUCT_DEPTH_BACKLOG.md`
- `docs/PRODUCT_DEPTH_GATE.md`
