# Beta Campaign Pack

Campaign status: `ready_to_invite`
Feedback status: `waiting_for_beta_signal`
Target beta records: `5`

## Privacy Guard

Do not request private datasets, raw images, private paths, or credentials.

## Outreach Copy

Try AlbumentationsX MCP on a small local image folder, keep data private, and share only redacted workflow symptoms plus generated artifact references.

## Workflow Cards

### robustness_distortion_variants

- Title: Robustness Distortion Variants
- Target user: CV engineer preparing robustness data
- Triage bucket: `workflow_fit_gap`
- Done when: Contact sheet and preview report are generated under artifact root.
- Record command: `uv run python scripts/record_beta_feedback.py --feedback-id beta-YYYYMMDD-robustness_distortion_variants --workflow-id robustness_distortion_variants --triage-bucket workflow_fit_gap --report-date YYYY-MM-DD --reporter-role '<redacted role>' --summary '<redacted workflow symptom>' --artifact-ref docs/assets/demo/demo_report.md --status new`
- MCP flow:
  - `run_host_smoke_check`
  - `build_review_packet`
  - `validate_preview_request`
  - `render_preview_batch`
  - `compare_preview_runs`
  - `export_preview_report`

### noisy_preview_tuning

- Title: Noisy Preview Tuning
- Target user: ML practitioner reviewing candidate augmentations
- Triage bucket: `review_agent_v3_gap`
- Done when: Feedback maps to structured tags and a revised candidate pipeline.
- Record command: `uv run python scripts/record_beta_feedback.py --feedback-id beta-YYYYMMDD-noisy_preview_tuning --workflow-id noisy_preview_tuning --triage-bucket review_agent_v3_gap --report-date YYYY-MM-DD --reporter-role '<redacted role>' --summary '<redacted workflow symptom>' --artifact-ref docs/assets/demo/demo_report.md --status new`
- MCP flow:
  - `interpret_preview_feedback`
  - `plan_preview_review`
  - `adjust_pipeline`
  - `render_preview_batch`
  - `record_tuning_decision`
  - `export_pipeline`

### dataset_health_before_training

- Title: Dataset Health Before Training
- Target user: Researcher checking annotations before training
- Triage bucket: `dataset_quality_gap`
- Done when: Dataset issues are reported before preview rendering starts.
- Record command: `uv run python scripts/record_beta_feedback.py --feedback-id beta-YYYYMMDD-dataset_health_before_training --workflow-id dataset_health_before_training --triage-bucket dataset_quality_gap --report-date YYYY-MM-DD --reporter-role '<redacted role>' --summary '<redacted workflow symptom>' --artifact-ref docs/assets/demo/demo_report.md --status new`
- MCP flow:
  - `inspect_dataset_quality`
  - `build_dataset_onboarding_report`
  - `build_review_packet`
  - `validate_preview_request`
  - `render_preview_batch`

## Triage Loop

- Collect redacted workflow symptoms until at least five beta records exist.
- Group repeated reports by workflow_id and triage_bucket.
- Convert repeated reports into failing tests before changing runtime behavior.
- Regenerate beta status, Review Agent v3 plan, and Dataset Quality plan after each accepted record batch.

## Source Docs

- `docs/BETA_WORKFLOW_PACK.md`
- `docs/BETA_FEEDBACK_INTAKE.md`
- `docs/BETA_FEEDBACK_STATUS.md`
- `docs/BETA_FEEDBACK_RECORDS.json`
