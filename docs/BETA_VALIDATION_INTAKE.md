# Beta Validation Intake

Intake status: `collecting_beta_validation`
Validation status: `manual_beta_required`
Feedback status: `waiting_for_beta_signal`
Records path: `docs/BETA_VALIDATION_RECORDS.json`

## Minimum Signal

Record at least one privacy-safe attempt for every beta workflow before product-depth reprioritization.

## Summary

- workflow_count: `3`
- missing_workflow_count: `3`
- recorded_workflow_count: `0`
- target_beta_records: `5`

## Privacy Checklist

- Do not request or commit private datasets, raw images, credentials, or unredacted local paths.
- Prefer synthetic/demo images and generated artifact references.
- Redact participant identity to a role, such as CV engineer or ML practitioner.
- Capture workflow symptoms and expected behavior instead of full host logs.

## Intake Lanes

| Workflow | Attempt Status | Issue Template | Record Command | Required Fields |
| --- | --- | --- | --- | --- |
| `robustness_distortion_variants` | `missing` | `.github/ISSUE_TEMPLATE/workflow-feedback.yml` | `uv run python scripts/record_beta_validation.py --workflow-id robustness_distortion_variants --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'CV engineer preparing robustness data' --summary 'Redacted beta attempt for robustness_distortion_variants.' --triage-bucket workflow_fit_gap --artifact-ref docs/assets/demo/demo_report.md` | `workflow_id`, `status`, `attempt_date`, `participant_role`, `summary`, `triage_bucket`, `artifact_ref` |
| `noisy_preview_tuning` | `missing` | `.github/ISSUE_TEMPLATE/workflow-feedback.yml` | `uv run python scripts/record_beta_validation.py --workflow-id noisy_preview_tuning --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'ML practitioner reviewing candidate augmentations' --summary 'Redacted beta attempt for noisy_preview_tuning.' --triage-bucket review_agent_v3_gap --artifact-ref docs/assets/demo/demo_report.md` | `workflow_id`, `status`, `attempt_date`, `participant_role`, `summary`, `triage_bucket`, `artifact_ref` |
| `dataset_health_before_training` | `missing` | `.github/ISSUE_TEMPLATE/dataset-health.yml` | `uv run python scripts/record_beta_validation.py --workflow-id dataset_health_before_training --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'Researcher checking annotations before training' --summary 'Redacted beta attempt for dataset_health_before_training.' --triage-bucket dataset_quality_gap --artifact-ref docs/assets/demo/demo_report.md` | `workflow_id`, `status`, `attempt_date`, `participant_role`, `summary`, `triage_bucket`, `artifact_ref` |

## Post-Intake Commands

- `uv run python scripts/validate_beta_validation_records.py`
- `uv run python scripts/export_beta_validation_status.py --output docs/BETA_VALIDATION_STATUS.md`
- `uv run python scripts/export_beta_campaign_execution.py --output docs/BETA_CAMPAIGN_EXECUTION.md`
- `uv run python scripts/export_beta_validation_intake.py --output docs/BETA_VALIDATION_INTAKE.md`
- `uv run python scripts/export_product_depth_gate.py --output docs/PRODUCT_DEPTH_GATE.md`
- `uv run python scripts/check_release_readiness.py`

## Source Docs

- `docs/BETA_CAMPAIGN_EXECUTION.md`
- `docs/BETA_VALIDATION_STATUS.md`
- `docs/BETA_VALIDATION_RECORDS.json`
- `.github/ISSUE_TEMPLATE/workflow-feedback.yml`
- `.github/ISSUE_TEMPLATE/dataset-health.yml`
