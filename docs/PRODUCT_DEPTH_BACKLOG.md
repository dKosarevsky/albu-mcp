# Product Depth Backlog

Backlog status: `waiting_for_beta_signal`

## Prioritization Rule

Do not promote depth work above P0 host evidence until RC gates pass.

## Backlog Items

| Triage Bucket | Product Area | Priority | Candidate | Success Signal |
| --- | --- | --- | --- | --- |
| `host_setup_gap` | `host_onboarding` | `p1_after_p0` | Host-specific setup probes and clearer blocked evidence capture. | A beta user can recover from setup failure without maintainer intervention. |
| `review_agent_v3_gap` | `preview_review_agent` | `p1_after_p0` | Feedback-to-adjustment planning that better handles noisy or unreadable previews. | Repeated noisy-preview feedback maps to safer candidate adjustments. |
| `dataset_quality_gap` | `dataset_quality` | `p1_after_p0` | Deeper dataset health findings for annotations, class balance, and duplicate handling. | Dataset issues are caught before preview rendering in beta workflows. |
| `docs_gap` | `host_docs` | `p2_after_beta` | Short host-specific cards for Codex, Claude Code, Cursor, and Claude Desktop. | Users can start the first preview without reading long-form docs. |
| `workflow_fit_gap` | `cv_workflow_templates` | `p2_after_beta` | More task-specific workflow templates for robustness, OCR, detection, and segmentation. | Beta users select a workflow template without custom prompting. |

## Quality Bar

- Convert repeated reports into tests before changing behavior.
- Keep local dataset privacy and bounded roots unchanged.
- Preserve public MCP contract snapshots for existing hosts.

## Source Docs

- `docs/BETA_FEEDBACK_INTAKE.md`
- `docs/BETA_VALIDATION_SPRINT.md`
- `docs/P0_HOST_EXECUTION_SPRINT.md`
- `docs/V1_RC_CUTOVER_CHECKLIST.md`
