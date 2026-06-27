# Beta Workflow Pack

## Trial Inputs

- `docs/FIRST_10_MINUTES.md`
- `docs/REAL_HOST_EVIDENCE_EXECUTION.md`
- `docs/BETA_WORKFLOW_PACK.md`

## Workflows

### robustness_distortion_variants

- Title: Robustness Distortion Variants
- Target user: CV engineer preparing robustness data
- Job: Make varied distorted previews for robustness review.
- Privacy boundary: local paths only; no dataset upload
- Done when: Contact sheet and preview report are generated under artifact root.
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
- Job: Interpret free-form feedback and plan a safer adjustment.
- Privacy boundary: local paths only; no dataset upload
- Done when: Feedback maps to structured tags and a revised candidate pipeline.
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
- Job: Inspect annotations before augmentation preview work.
- Privacy boundary: local paths only; no dataset upload
- Done when: Dataset issues are reported before preview rendering starts.
- MCP flow:
  - `inspect_dataset_quality`
  - `build_dataset_onboarding_report`
  - `build_review_packet`
  - `validate_preview_request`
  - `render_preview_batch`

## Success Criteria

- User can render a contact sheet from local images.
- User can reject an over-noisy candidate without reading docs.
- User can inspect dataset health before augmentation preview work.
