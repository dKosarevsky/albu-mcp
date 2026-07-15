# First 10 Minutes Host Prompt

Copy this into an MCP-capable host after connecting AlbumentationsX MCP.

```text
Use AlbumentationsX MCP for a first 10-minute augmentation review.

Local image or dataset folder:
/absolute/path/to/images-or-dataset

First, read albumentationsx://examples/client-smoke. If resource reads are unavailable, call get_workflow_example with
example_id="client-smoke". Then run run_host_smoke_check.
Continue only if preview_ready is true. If it is not ready, explain the remediation actions and stop before rendering.

Then call plan_dataset_onboarding for the local image or directory. Use preview_request_template as the starting point.
Do not render anything until validate_preview_request returns valid=true.

Render a small preview with render_preview_batch:
- use one variant per image;
- keep the first pipeline conservative;
- write artifacts under the configured artifact root;
- create a contact sheet;
- summarize what changed in visual terms.

After I inspect the contact sheet, ask for concrete feedback. If I say that some examples are too noisy, too blurry,
too distorted, or too dark, call adjust_pipeline and render a candidate preview.

Compare the baseline and candidate with compare_preview_runs before exporting anything.

When I accept the result, call export_pipeline and provide:
- Python code for the accepted AlbumentationsX pipeline;
- JSON for review;
- the seed and target assumptions;
- a short note about the feedback that led to the final version.

If my local image source is not ready, show me the reference demo report path instead:
docs/assets/demo/demo_report.md
```
