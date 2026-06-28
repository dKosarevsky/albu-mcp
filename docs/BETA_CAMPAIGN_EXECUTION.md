# Beta Campaign Execution

Execution status: `ready_to_invite`
Validation status: `manual_beta_required`
Feedback status: `waiting_for_beta_signal`

## Privacy Guard

Do not request private datasets, raw images, private paths, or credentials.

## Outreach Copy

Try AlbumentationsX MCP on a small local image folder, keep data private, and share only redacted workflow symptoms plus generated artifact references.

## Summary

- workflow_count: `3`
- missing_workflow_count: `3`
- recorded_workflow_count: `0`
- target_beta_records: `5`

## Invite Lanes

| Workflow | Attempt Status | Next Action | Validation Record Command |
| --- | --- | --- | --- |
| `robustness_distortion_variants` | `missing` | `invite_beta_user` | `uv run python scripts/record_beta_validation.py --workflow-id robustness_distortion_variants --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'CV engineer preparing robustness data' --summary 'Redacted beta attempt for robustness_distortion_variants.' --triage-bucket workflow_fit_gap --artifact-ref docs/assets/demo/demo_report.md` |
| `noisy_preview_tuning` | `missing` | `invite_beta_user` | `uv run python scripts/record_beta_validation.py --workflow-id noisy_preview_tuning --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'ML practitioner reviewing candidate augmentations' --summary 'Redacted beta attempt for noisy_preview_tuning.' --triage-bucket review_agent_v3_gap --artifact-ref docs/assets/demo/demo_report.md` |
| `dataset_health_before_training` | `missing` | `invite_beta_user` | `uv run python scripts/record_beta_validation.py --workflow-id dataset_health_before_training --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'Researcher checking annotations before training' --summary 'Redacted beta attempt for dataset_health_before_training.' --triage-bucket dataset_quality_gap --artifact-ref docs/assets/demo/demo_report.md` |

## Completion Rule

Collect at least one privacy-safe validation record for each beta workflow before product-depth reprioritization.

## Post-Recording Commands

- `uv run python scripts/validate_beta_validation_records.py`
- `uv run python scripts/export_beta_validation_status.py --output docs/BETA_VALIDATION_STATUS.md`
- `uv run python scripts/export_beta_campaign_execution.py --output docs/BETA_CAMPAIGN_EXECUTION.md`
- `uv run python scripts/export_product_depth_gate.py --output docs/PRODUCT_DEPTH_GATE.md`

## Source Docs

- `docs/BETA_CAMPAIGN_PACK.md`
- `docs/BETA_VALIDATION_STATUS.md`
- `docs/BETA_VALIDATION_RECORDS.json`
