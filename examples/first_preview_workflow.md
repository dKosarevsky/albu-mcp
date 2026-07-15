# First Preview Workflow

Use this same workflow after configuring AlbumentationsX MCP in Claude Desktop, Claude Code, Cursor, or Codex.

1. Read `albumentationsx://examples/client-smoke`; if resource reads are unavailable, call `get_workflow_example` with `example_id="client-smoke"`.
2. Call `run_host_smoke_check`.
3. Continue only when `preview_ready` is true.
4. Copy `preview_request_template.request`.
5. Replace the placeholder `input_paths` value with one small image under `--allowed-root`.
6. Call `validate_preview_request` with the filled request.
7. Call `render_preview_batch` only when validation returns `valid: true`.
8. Inspect the returned contact sheet before increasing intensity, batch size, or variants.

Example host instruction:

```text
Read albumentationsx://examples/client-smoke. If resource reads are unavailable, call get_workflow_example with example_id="client-smoke". Then call run_host_smoke_check for classification. If preview_ready is true, copy preview_request_template.request, replace input_paths with /absolute/path/to/images/sample.jpg, call validate_preview_request, and render one preview batch only if the request is valid.
```
