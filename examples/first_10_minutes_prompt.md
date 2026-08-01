# First 10 Minutes Host Prompt

Copy this into an MCP-capable host after connecting AlbumentationsX MCP.

```text
Use AlbumentationsX MCP for a first 10-minute augmentation review.

Local image or dataset folder:
/absolute/path/to/images-or-dataset

The guided run_first_preview workflow requires the default full or dataset capability profile.

First, read albumentationsx://examples/client-smoke. If resource reads are unavailable, call get_workflow_example with
example_id="client-smoke". Then run run_host_smoke_check.
Continue only if preview_ready is true. If it is not ready, explain the remediation actions and stop before rendering.

Then call run_first_preview for the local image or directory with intensity="low" and max_images=8. Show me the
returned contact sheet.

When I identify a specific result, call trace_preview_variant with the returned run id and that result's zero-based
image_index and variant_index. Summarize the applied transforms before adjusting anything.

After the trace, ask for concrete feedback. If I say that some examples are too noisy, too blurry, too distorted, or
too dark, call adjust_pipeline and render a candidate preview.

Compare the baseline and candidate with compare_preview_runs before exporting anything.

When I accept the result, call export_pipeline and provide:
- Python code for the accepted AlbumentationsX pipeline;
- JSON for review;
- the seed and target assumptions;
- a short note about the feedback that led to the final version.

Explicit fallback:
In the review capability profile, or when I ask to inspect the request, continue after run_host_smoke_check returns
preview_ready=true. Copy preview_request_template.request and replace its placeholder path.
In full or dataset, you may call plan_dataset_onboarding before validation and use its returned request instead. The
review profile must not call that unavailable tool and continues with preview_request_template from the smoke report.
Call validate_preview_request with that request.
Do not render anything until validate_preview_request returns valid=true.
Then call render_preview_batch and inspect its contact sheet. When I identify a result, call trace_preview_variant with
its zero-based indexes. Call adjust_pipeline after the trace, render a candidate, and use compare_preview_runs.
Call export_pipeline only after I accept the result.

If my local image source is not ready, show me the reference demo report path:
docs/assets/demo/demo_report.md
```
