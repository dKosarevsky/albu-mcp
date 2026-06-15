# v1.5 Real Sample Smoke Design

## Context

v1.4 added `run_host_smoke_check`, which proves the MCP host can discover tools, validate a recommended recipe, and return a safe `render_preview_batch` template. The remaining gap is end-to-end proof that the template can be filled with real local image paths, render preview artifacts, read the manifest, compare a candidate run, and clean up generated runs through the same stdio MCP path a host uses.

## Goal

Add a golden eval scenario that exercises the first-preview workflow on deterministic non-uniform sample images, without adding a new runtime dependency or expanding the server API unnecessarily.

## Options Considered

1. Add a new MCP tool that creates bundled demo images.
   This would make demos convenient, but it would also make the server write source-like input files and expand the public API for a test helper.

2. Add a new MCP resource that embeds sample image data.
   This keeps the workflow discoverable, but MCP hosts still need local files for preview rendering, and base64 images would bloat resource payloads.

3. Keep sample generation in the golden runner and document the user-facing workflow.
   This validates the actual MCP tools over stdio while keeping runtime boundaries clean. Users still provide their own image paths, which matches the product model.

Chosen approach: option 3.

## Architecture

The golden runner owns test fixture generation because sample images are verification inputs, not product data. It will generate deterministic RGB PNGs under the already configured `--allowed-root`, call `run_host_smoke_check`, replace the placeholder path in `preview_request_template.request`, render a baseline preview, adjust the pipeline from feedback, render a candidate preview, compare both runs, assert quality metrics exist, then delete both runs.

The MCP server remains unchanged unless documentation or workflow resources need wording updates. This keeps production boundaries simple: server tools read only user-approved input paths and write only under the artifact root.

## Data Flow

1. Golden runner starts the MCP server with `--allowed-root <work-dir>/images` and `--artifact-root <work-dir>/artifacts`.
2. Scenario `real_sample_preview_smoke` writes deterministic sample images into `<work-dir>/images/real-sample-preview-smoke/`.
3. Runner calls `run_host_smoke_check` and verifies `preview_ready=true`.
4. Runner copies `preview_request_template.request`, replaces `input_paths`, applies the scenario seed and max side, and calls `render_preview_batch`.
5. Runner calls `adjust_pipeline`, renders a candidate with the same sample inputs, and calls `compare_preview_runs`.
6. Runner asserts image artifacts, contact sheet artifacts, manifest summary, and quality summary are present.
7. Runner deletes both preview runs and verifies cleanup through tool responses.

## Error Handling

The scenario should fail with explicit assertion messages when the host smoke report is not preview-ready, the template is unsafe, generated inputs are missing or uniform, manifests lack contact sheets, comparison quality metrics are absent, or cleanup fails. The sample image helper should write only below the provided allowed root and should return stable paths.

## Testing

Tests will first assert the new scenario is declared and that the runner contains the real sample smoke path. A focused unit test will verify generated sample images are non-uniform RGB PNGs. The full golden eval test will execute the scenario over stdio and must report `real_sample_preview_smoke: ok`.

## Scope

This change does not add a public MCP tool, does not change output contracts, and does not require a contract snapshot update. It may justify a minor release because the project’s published verification and documentation now cover the complete first-preview path.
