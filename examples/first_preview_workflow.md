# First Preview Workflow

Use this workflow after configuring AlbumentationsX MCP in Claude Desktop, Claude Code, Cursor, or Codex.

## Guided path: full or dataset

The preferred `run_first_preview` path requires the default `full` or `dataset` capability profile.

1. Read `albumentationsx://examples/client-smoke`; if resource reads are unavailable, call `get_workflow_example` with `example_id="client-smoke"`.
2. Call `run_host_smoke_check`.
3. Continue only when `preview_ready` is true.
4. Call `run_first_preview` for the image or directory with low intensity and no more than eight images.
5. Inspect the contact sheet.
6. Call `trace_preview_variant` for the selected zero-based image and variant indexes.
7. Call `adjust_pipeline`, render the candidate, and use `compare_preview_runs`.
8. Call `export_pipeline` only after accepting the result.

## Explicit review fallback

The `review` profile does not expose `run_first_preview`. Use the smoke report's manual request instead:

1. Call `run_host_smoke_check` and continue only when `preview_ready` is true.
2. Copy `preview_request_template.request` and replace its placeholder path with an image under `--allowed-root`.
3. Call `validate_preview_request` with the filled request.
4. Call `render_preview_batch` only when validation returns `valid=true`.
5. Inspect the contact sheet, then call `trace_preview_variant` for the selected result.
6. Adjust, render, compare, and export only after acceptance.

Example host instruction:

```text
Read albumentationsx://examples/client-smoke. If resource reads are unavailable, call get_workflow_example with
example_id="client-smoke". Then call run_host_smoke_check for classification. If preview_ready is true and
run_first_preview is available, call it for /absolute/path/to/images with low intensity and at most 8 images. Show me
the contact sheet, then trace the selected variant before adjusting it. If run_first_preview is unavailable, use
preview_request_template, validate it, and render_preview_batch only when valid=true; then inspect and trace the result.
```
