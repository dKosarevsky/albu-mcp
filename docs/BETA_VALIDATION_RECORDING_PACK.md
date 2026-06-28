# Beta Validation Recording Pack

Recording status: `manual_records_required`
Validation status: `manual_beta_required`
Records path: `docs/BETA_VALIDATION_RECORDS.json`

## Recording Policy

Record only real beta attempts. Synthetic examples can be referenced as artifacts, but they do not replace participant-observed workflow symptoms.

## Summary

- record_count: `0`
- workflow_count: `3`
- missing_workflow_count: `3`
- covered_workflow_count: `0`
- private_data_record_count: `0`

## Accepted Statuses

- `passed`
- `blocked`
- `needs_followup`

## Privacy Checklist

- Do not request or commit private datasets, raw images, credentials, or unredacted local paths.
- Prefer synthetic/demo images and generated artifact references.
- Redact participant identity to a role, such as CV engineer or ML practitioner.
- Capture workflow symptoms and expected behavior instead of full host logs.

## Recording Lanes

| Workflow | Attempt Status | Issue Template | Command | Acceptance Note |
| --- | --- | --- | --- | --- |
| `robustness_distortion_variants` | `missing` | `.github/ISSUE_TEMPLATE/workflow-feedback.yml` | `uv run python scripts/record_beta_validation.py --workflow-id robustness_distortion_variants --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'CV engineer preparing robustness data' --summary 'Redacted beta attempt for robustness_distortion_variants.' --triage-bucket workflow_fit_gap --artifact-ref docs/assets/demo/demo_report.md` | Use this command only after a real participant attempt produces a redacted symptom summary. |
| `noisy_preview_tuning` | `missing` | `.github/ISSUE_TEMPLATE/workflow-feedback.yml` | `uv run python scripts/record_beta_validation.py --workflow-id noisy_preview_tuning --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'ML practitioner reviewing candidate augmentations' --summary 'Redacted beta attempt for noisy_preview_tuning.' --triage-bucket review_agent_v3_gap --artifact-ref docs/assets/demo/demo_report.md` | Use this command only after a real participant attempt produces a redacted symptom summary. |
| `dataset_health_before_training` | `missing` | `.github/ISSUE_TEMPLATE/dataset-health.yml` | `uv run python scripts/record_beta_validation.py --workflow-id dataset_health_before_training --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'Researcher checking annotations before training' --summary 'Redacted beta attempt for dataset_health_before_training.' --triage-bucket dataset_quality_gap --artifact-ref docs/assets/demo/demo_report.md` | Use this command only after a real participant attempt produces a redacted symptom summary. |

## Post-Recording Commands

- `uv run python scripts/validate_beta_validation_records.py`
- `uv run python scripts/export_beta_validation_status.py --output docs/BETA_VALIDATION_STATUS.md`
- `uv run python scripts/export_beta_validation_intake.py --output docs/BETA_VALIDATION_INTAKE.md`
- `uv run python scripts/export_beta_validation_recording_pack.py --output docs/BETA_VALIDATION_RECORDING_PACK.md`
- `uv run python scripts/export_product_depth_gate.py --output docs/PRODUCT_DEPTH_GATE.md`
- `uv run python scripts/check_release_readiness.py`

## Source Docs

- `docs/BETA_VALIDATION_INTAKE.md`
- `docs/BETA_VALIDATION_STATUS.md`
- `docs/BETA_VALIDATION_RECORDS.json`
- `.github/ISSUE_TEMPLATE/workflow-feedback.yml`
- `.github/ISSUE_TEMPLATE/dataset-health.yml`
