# Distortion Review Workflow

Use this when a user asks for distorted robustness examples and then rejects a concrete preview:

```text
Read albumentationsx://examples/distortion-review. If resource reads are unavailable, call get_workflow_example with
example_id="distortion-review". Start with run_host_smoke_check for classification. Validate the filled
preview_request_template with validate_preview_request. Render a small render_preview_batch. If the user says
"example 8 is too noisy", record that exact feedback with record_preview_feedback, adjust the pipeline, compare the
runs, and export only the accepted candidate.
```

Useful sequence:

1. Read `albumentationsx://examples/distortion-review`; if resource reads are unavailable, call `get_workflow_example` with `example_id="distortion-review"`.
2. Call `run_host_smoke_check`.
3. Fill and validate `preview_request_template.request`.
4. Call `render_preview_batch`.
5. Record concrete notes with `record_preview_feedback`.
6. Call `adjust_pipeline`.
7. Call `compare_preview_runs`.
8. Call `export_pipeline` only after acceptance.
