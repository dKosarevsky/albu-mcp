# Beta Feedback Intake

## Privacy Policy

Collect workflow symptoms and redacted artifacts, never private datasets.

## Workflow Intake

### robustness_distortion_variants

- Target user: CV engineer preparing robustness data
- Job: Make varied distorted previews for robustness review.
- Triage hint: `workflow_fit_gap`
- Expected feedback:
  - Contact sheet path
  - Preview report path
  - Accepted/rejected candidate
  - Reason for rejection

### noisy_preview_tuning

- Target user: ML practitioner reviewing candidate augmentations
- Job: Interpret free-form feedback and plan a safer adjustment.
- Triage hint: `review_agent_v3_gap`
- Expected feedback:
  - Free-form user note
  - Structured feedback tags
  - Recommended next MCP tool
  - Whether the revised candidate became acceptable

### dataset_health_before_training

- Target user: Researcher checking annotations before training
- Job: Inspect annotations before augmentation preview work.
- Triage hint: `dataset_quality_gap`
- Expected feedback:
  - Dataset quality findings
  - Annotation format
  - Whether preview was blocked
  - Requested follow-up

## Triage Buckets

- `host_setup_gap`
- `review_agent_v3_gap`
- `dataset_quality_gap`
- `docs_gap`
- `workflow_fit_gap`

## Weekly Loop

- Review new feedback issues and manual beta notes.
- Group reports by triage bucket and affected workflow.
- Convert repeated reports into tests before changing behavior.
- Regenerate beta docs and release readiness reports after accepted changes.
