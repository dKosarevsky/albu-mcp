# Beta Attempt Capture Kit

Kit status: `manual_attempts_required`
Records path: `docs/BETA_VALIDATION_RECORDS.json`

## Privacy Policy

Never collect private datasets, tokens, screenshots, or full host logs.

## Summary

- workflow_count: `3`
- record_count: `0`
- missing_workflow_count: `3`

## Attempt Lanes

| Workflow | Attempt Status | Issue Template | Record Command | Acceptance Note |
| --- | --- | --- | --- | --- |
| `robustness_distortion_variants` | `missing` | `.github/ISSUE_TEMPLATE/workflow-feedback.yml` | `uv run python scripts/record_beta_validation.py --workflow-id robustness_distortion_variants --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'CV engineer preparing robustness data' --summary 'Redacted beta attempt for robustness_distortion_variants.' --triage-bucket workflow_fit_gap --artifact-ref docs/assets/demo/demo_report.md` | Use this command only after a real participant attempt produces a redacted symptom summary. |
| `noisy_preview_tuning` | `missing` | `.github/ISSUE_TEMPLATE/workflow-feedback.yml` | `uv run python scripts/record_beta_validation.py --workflow-id noisy_preview_tuning --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'ML practitioner reviewing candidate augmentations' --summary 'Redacted beta attempt for noisy_preview_tuning.' --triage-bucket review_agent_v3_gap --artifact-ref docs/assets/demo/demo_report.md` | Use this command only after a real participant attempt produces a redacted symptom summary. |
| `dataset_health_before_training` | `missing` | `.github/ISSUE_TEMPLATE/dataset-health.yml` | `uv run python scripts/record_beta_validation.py --workflow-id dataset_health_before_training --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'Researcher checking annotations before training' --summary 'Redacted beta attempt for dataset_health_before_training.' --triage-bucket dataset_quality_gap --artifact-ref docs/assets/demo/demo_report.md` | Use this command only after a real participant attempt produces a redacted symptom summary. |

## Record Writer

`scripts/record_beta_validation.py` is the only beta attempt writer.

## Post-Attempt Commands

- `uv run python scripts/validate_beta_validation_records.py`
- `uv run python scripts/export_beta_validation_status.py --output docs/BETA_VALIDATION_STATUS.md`
- `uv run python scripts/export_beta_to_backlog_triage.py --output docs/BETA_TO_BACKLOG_TRIAGE.md`
- `uv run python scripts/check_release_readiness.py`

## Source Docs

- `docs/BETA_VALIDATION_RECORDING_PACK.md`
- `docs/BETA_VALIDATION_LOOP.md`
- `docs/BETA_VALIDATION_RECORDS.json`
