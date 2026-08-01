# First 10 Minutes Host Prompt

Copy this into an MCP-capable host after connecting AlbumentationsX MCP.

```text
Use AlbumentationsX MCP for a first 10-minute augmentation review.

Local image or dataset folder:
/absolute/path/to/images-or-dataset

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

Explicit advanced/fallback path:
If run_first_preview is unavailable or I ask to inspect the request, continue after run_host_smoke_check returns
preview_ready=true: call plan_dataset_onboarding and use preview_request_template as the starting point.
Do not render anything until validate_preview_request returns valid=true.
Then call render_preview_batch, inspect its contact sheet, use compare_preview_runs after adjustments, and call
export_pipeline only after I accept the result.

If my local image source is not ready, show me the reference demo report path:
docs/assets/demo/demo_report.md
```
