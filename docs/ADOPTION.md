# Adoption Packet

Use this page when sharing AlbumentationsX MCP with maintainers, MCP host users, or computer-vision teams that need a
quick trial before reading the full docs.

For the shortest hands-on path, send users to [docs/FIRST_10_MINUTES.md](FIRST_10_MINUTES.md). It takes them from
installation to smoke check, preview, feedback, comparison, and export.

## 2-minute trial

Run the published package:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
```

For preview rendering, restart the server with explicit local bounds:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp \
  --allowed-root /absolute/path/to/images \
  --artifact-root /absolute/path/to/albu-artifacts
```

Then ask the host:

```text
Read albumentationsx://examples/client-smoke, run run_host_smoke_check, then help me create a small augmentation
preview for images under my allowed root.
```

For a fuller copyable prompt, use `examples/first_10_minutes_prompt.md`.

## Host setup

- Claude Desktop: use the PyPI config in `examples/claude_desktop_pypi_config.json`.
- Claude Code: use `examples/claude_code_preview_command.md`.
- Cursor: use `examples/cursor_preview_mcp_config.json`.
- Codex: use `examples/codex_preview_mcp_config.toml`.

Run `plan_dataset_onboarding` before rendering a real folder. It samples local images, detects common layouts, and
returns a bounded `preview_request_template` for `validate_preview_request` and `render_preview_batch`.

## Good first workflows

- Classification: render a small contact sheet, reject examples that are too blurry, then call `adjust_pipeline`.
- Detection: use COCO or YOLO labels and inspect `overlay_contact_sheet` before accepting geometric transforms.
- Segmentation: use segmentation datasets with COCO polygons, compressed COCO RLE, uncompressed COCO RLE, or YOLO-seg
  polygons with `["image", "mask"]` targets.
- Robustness review: compare baseline and candidate runs with `compare_preview_runs`, then `export_pipeline`.

## Copyable outreach note

```markdown
I am trying AlbumentationsX MCP for interactive augmentation review. It lets an MCP host discover transforms, validate
pipelines, render deterministic local previews, compare preview runs, and export an accepted pipeline. The useful loop is
"show me distorted variants", "this one is too noisy", "reduce that", and then export the final pipeline.

Project: https://github.com/dKosarevsky/albu-mcp
Package: https://pypi.org/project/albumentationsx-mcp/
```

## Feedback channels

- Host compatibility: use `.github/ISSUE_TEMPLATE/host-acceptance.yml`.
- Workflow gaps: use `.github/ISSUE_TEMPLATE/workflow-feedback.yml`.
- Feature ideas: use `.github/ISSUE_TEMPLATE/feature-request.yml`.

Keep private datasets and proprietary paths out of issues. Prefer synthetic images, redacted contact sheets, or generated
reports from `docs/assets/demo/`.
