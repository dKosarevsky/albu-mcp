# Beta Validation Sprint

Validation status: `manual_beta_required`

## Privacy Policy

Collect workflow symptoms and redacted artifacts, never private datasets.

## Minimum Signal

At least one real user attempt per beta workflow before product-depth reprioritization.

## Participant Slots

### robustness_distortion_variants

- Target user: CV engineer preparing robustness data
- Job: Make varied distorted previews for robustness review.
- Done when: Contact sheet and preview report are generated under artifact root.
- MCP flow:
  - `run_host_smoke_check`
  - `build_review_packet`
  - `validate_preview_request`
  - `render_preview_batch`
  - `compare_preview_runs`
  - `export_preview_report`
- Expected feedback:
  - Contact sheet path
  - Preview report path
  - Accepted/rejected candidate
  - Reason for rejection

### noisy_preview_tuning

- Target user: ML practitioner reviewing candidate augmentations
- Job: Interpret free-form feedback and plan a safer adjustment.
- Done when: Feedback maps to structured tags and a revised candidate pipeline.
- MCP flow:
  - `interpret_preview_feedback`
  - `plan_preview_review`
  - `adjust_pipeline`
  - `render_preview_batch`
  - `record_tuning_decision`
  - `export_pipeline`
- Expected feedback:
  - Free-form user note
  - Structured feedback tags
  - Recommended next MCP tool
  - Whether the revised candidate became acceptable

### dataset_health_before_training

- Target user: Researcher checking annotations before training
- Job: Inspect annotations before augmentation preview work.
- Done when: Dataset issues are reported before preview rendering starts.
- MCP flow:
  - `inspect_dataset_quality`
  - `build_dataset_onboarding_report`
  - `build_review_packet`
  - `validate_preview_request`
  - `render_preview_batch`
- Expected feedback:
  - Dataset quality findings
  - Annotation format
  - Whether preview was blocked
  - Requested follow-up

## Recording Commands

- `uv run python scripts/record_beta_validation.py --workflow-id robustness_distortion_variants --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'CV engineer preparing robustness data' --summary 'Redacted real beta workflow attempt summary.' --triage-bucket workflow_fit_gap --artifact-ref docs/assets/demo/demo_report.md`
- `uv run python scripts/record_beta_validation.py --workflow-id noisy_preview_tuning --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'ML practitioner reviewing candidate augmentations' --summary 'Redacted real beta workflow attempt summary.' --triage-bucket review_agent_v3_gap --artifact-ref docs/assets/demo/demo_report.md`
- `uv run python scripts/record_beta_validation.py --workflow-id dataset_health_before_training --status needs_followup --attempt-date YYYY-MM-DD --participant-role 'Researcher checking annotations before training' --summary 'Redacted real beta workflow attempt summary.' --triage-bucket dataset_quality_gap --artifact-ref docs/assets/demo/demo_report.md`
## Triage Buckets

- `host_setup_gap`
- `review_agent_v3_gap`
- `dataset_quality_gap`
- `docs_gap`
- `workflow_fit_gap`

## Weekly Cadence

- Review new GitHub issues, beta notes, and redacted artifact references.
- Map every report to one workflow and one triage bucket.
- Convert repeated beta reports into tests before changing behavior.
- Regenerate docs/BETA_FEEDBACK_INTAKE.md and docs/PRODUCT_DEPTH_BACKLOG.md after accepted changes.

## Exit Criteria

- Each beta workflow has at least one real user attempt.
- Every blocker is either reproduced, triaged, or explicitly marked insufficient evidence.
- No private datasets, tokens, screenshots, or full host logs are collected.
