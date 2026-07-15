# First 10 Minutes

This guide is the shortest path from installation to a useful AlbumentationsX MCP result:

1. start the server with bounded local access;
2. connect it to an MCP host;
3. run the host smoke check;
4. render a small preview batch;
5. give feedback;
6. export the accepted pipeline.

For full installation details, see [docs/INSTALL.md](INSTALL.md). For the complete tool workflow, see
[docs/USAGE.md](USAGE.md).

## What you should have after 10 minutes

- a working MCP server process;
- a host-visible `run_host_smoke_check` result;
- a validated preview request for one local image or a small image directory;
- a contact sheet or a reference demo report;
- one feedback-driven candidate pipeline;
- an exported Python or JSON pipeline.

If you do not have local images ready, use the committed reference demo in
[docs/assets/demo/demo_report.md](assets/demo/demo_report.md) to understand the expected review artifact before
connecting a real dataset.

## 0-2 minutes: start the server

Run the published package:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
```

For real preview rendering, restart with explicit local bounds:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp \
  --allowed-root /absolute/path/to/images-or-dataset \
  --artifact-root /absolute/path/to/albu-artifacts
```

`--allowed-root` is the only local tree the server may read. `--artifact-root` is where generated contact sheets,
manifests, reports, and exports are written.

## 2-4 minutes: connect a host

Use the host-specific snippets in [examples](../examples/):

- Claude Desktop: `examples/claude_desktop_preview_config.json`
- Claude Code: `examples/claude_code_preview_command.md`
- Cursor: `examples/cursor_preview_mcp_config.json`
- Codex: `examples/codex_preview_mcp_config.toml`

After editing host configuration, refresh MCP discovery or restart the host.

## 4-6 minutes: run the smoke check

Ask the host:

```text
Read albumentationsx://examples/client-smoke. If resource reads are unavailable, call
get_workflow_example with example_id="client-smoke". Then run run_host_smoke_check.
Continue only if preview_ready is true. If it is not ready, explain the remediation actions.
```

The smoke check verifies environment basics, bounded preview roots, artifact output, recipe recommendation, pipeline
validation, and a preview request template. Fix this before rendering any local image paths.

## 6-8 minutes: render a first preview

Use the copyable prompt in [examples/first_10_minutes_prompt.md](../examples/first_10_minutes_prompt.md). Replace the
dataset path with a folder under `--allowed-root`.

The host should follow this sequence:

1. call `plan_dataset_onboarding`;
2. inspect the returned `preview_request_template`;
3. call `validate_preview_request`;
4. call `render_preview_batch` only after validation succeeds;
5. open the contact sheet and summarize what changed.

For detection and segmentation folders, onboarding can detect common COCO, YOLO, COCO segmentation, COCO RLE, and
YOLO-seg layouts. The generated template keeps masks and bounding boxes aligned with the declared pipeline targets.

## 8-10 minutes: tune and export

Give concrete feedback:

```text
The geometric variation is useful, but examples 3 and 8 are too noisy. Reduce noise and keep the crop/flip behavior.
Compare the adjusted preview with the baseline before exporting anything.
```

The host should then call:

1. `adjust_pipeline` to create a candidate;
2. `render_preview_batch` to render the candidate;
3. `compare_preview_runs` to compare baseline and candidate manifests;
4. `export_pipeline` when you accept the result.

Ask for Python when you want code for a training pipeline. Ask for JSON or YAML when you want a reviewable configuration
artifact.

## Fallback demo path

If host setup is not ready yet, inspect the deterministic demo:

- report: [docs/assets/demo/demo_report.md](assets/demo/demo_report.md)
- baseline contact sheet: [docs/assets/demo/contact_sheet.png](assets/demo/contact_sheet.png)
- comparison contact sheet: [docs/assets/demo/comparison_contact_sheet.png](assets/demo/comparison_contact_sheet.png)

Refresh the demo locally with:

```bash
uv run python scripts/render_demo_assets.py --output-dir docs/assets/demo
uv run python scripts/check_demo_assets.py --output-dir docs/assets/demo --check
```

## Readiness guard

This quick path is protected by a local check:

```bash
uv run python scripts/check_first_10_minutes.py
```

The release readiness script runs the same guard so the README entrypoint, quickstart guide, host prompt, and demo
artifacts do not drift apart.

## Manual host replay

After a real MCP host completes this workflow, record the result separately from the broader host acceptance gate:

```bash
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed \
  --date 2026-06-22 \
  --evidence "Codex completed smoke check, preview validation, baseline and candidate render, comparison, and export." \
  --artifact docs/assets/demo/demo_report.md
uv run python scripts/check_first_10_minutes_replay.py --host Codex
```

Use `blocked` instead of `passed` when the host cannot complete the workflow, and include the concrete blocker in
`--evidence`.
