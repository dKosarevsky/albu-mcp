# Beta Validation Loop

Loop status: `manual_beta_required`
Records path: `docs/BETA_VALIDATION_RECORDS.json`
Next operator action: Recruit one real user attempt for each missing beta workflow.

## Privacy Policy

Collect workflow symptoms and redacted artifacts, never private datasets.

No private datasets, tokens, screenshots, or full host logs are collected.

## Minimum Signal

At least one real user attempt per beta workflow before product-depth reprioritization.

## Summary

- workflow_count: `3`
- record_count: `0`
- covered_workflow_count: `0`
- missing_workflow_count: `3`

## Workflow Lanes

| Workflow | Status | Attempt Date | Triage Bucket | Summary |
| --- | --- | --- | --- | --- |
| `dataset_health_before_training` | `missing` | `not_recorded` | `not_recorded` | No real beta workflow attempt recorded. |
| `noisy_preview_tuning` | `missing` | `not_recorded` | `not_recorded` | No real beta workflow attempt recorded. |
| `robustness_distortion_variants` | `missing` | `not_recorded` | `not_recorded` | No real beta workflow attempt recorded. |

## Recording Commands

`scripts/record_beta_validation.py` is the only beta validation record writer.

- `uv run python scripts/record_beta_validation.py --workflow-id robustness_distortion_variants --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'CV engineer preparing robustness data' --summary 'Redacted beta attempt for robustness_distortion_variants.' --triage-bucket workflow_fit_gap --artifact-ref docs/assets/demo/demo_report.md`
- `uv run python scripts/record_beta_validation.py --workflow-id noisy_preview_tuning --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'ML practitioner reviewing candidate augmentations' --summary 'Redacted beta attempt for noisy_preview_tuning.' --triage-bucket review_agent_v3_gap --artifact-ref docs/assets/demo/demo_report.md`
- `uv run python scripts/record_beta_validation.py --workflow-id dataset_health_before_training --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'Researcher checking annotations before training' --summary 'Redacted beta attempt for dataset_health_before_training.' --triage-bucket dataset_quality_gap --artifact-ref docs/assets/demo/demo_report.md`

## Loop Cadence

- Recruit or observe one real user attempt for each missing workflow.
- Record only redacted symptoms and artifact references.
- Run validation and regenerate beta status after every record.
- Promote repeated findings only after the workflow has real signal.

## Exit Criteria

- Each beta workflow has at least one real user attempt.
- Every blocker is either reproduced, triaged, or explicitly marked insufficient evidence.
- No private datasets, tokens, screenshots, or full host logs are collected.

## Post-Record Commands

- `uv run python scripts/validate_beta_validation_records.py`
- `uv run python scripts/export_beta_validation_status.py --output docs/BETA_VALIDATION_STATUS.md`
- `uv run python scripts/export_beta_to_backlog_triage.py --output docs/BETA_TO_BACKLOG_TRIAGE.md`
- `uv run python scripts/export_beta_validation_loop.py --output docs/BETA_VALIDATION_LOOP.md`
- `uv run python scripts/check_release_readiness.py`

## Source Docs

- `docs/BETA_VALIDATION_RECORDS.json`
- `docs/BETA_VALIDATION_RECORDING_PACK.md`
- `docs/BETA_VALIDATION_SPRINT.md`
- `docs/BETA_VALIDATION_STATUS.md`
- `docs/BETA_TO_BACKLOG_TRIAGE.md`
