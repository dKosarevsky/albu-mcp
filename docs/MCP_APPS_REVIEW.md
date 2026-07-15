# Interactive Preview Review

AlbumentationsX MCP adds an MCP Apps review surface to `render_preview` and `render_preview_batch`.
The UI uses progressive enhancement: the render tool contract, preview artifacts, and feedback tools remain usable
without the UI.

The app is available in the `review`, `dataset`, and `full` capability profiles. Each of those profiles includes
`record_preview_feedback`; `core` publishes neither the preview app nor local render tools.

## What Opens

A compatible host reads the packaged resource:

```text
ui://albumentationsx/preview-review.html
```

The resource uses `text/html;profile=mcp-app` and contains its JavaScript, CSS, icons, and SDK runtime in one HTML file.
It has no outgoing network dependency. Installing or upgrading `albumentationsx-mcp` installs the UI with the Python
package; there is no separate web service, browser extension, or frontend package for users to install.

## Review Flow

1. The host calls `render_preview` or `render_preview_batch` as usual.
2. The tool returns ordinary text and structured content, including the run id and artifact references.
3. A compatible host opens the associated MCP App and forwards the tool result.
4. The app builds an ordinal review list such as `Image 2 / Variant 3`; it does not retain source image paths.
5. The app asks the server for the selected image or overlay through `artifact://{run_id}/{filename}`.
6. The reviewer selects issues, severity, an optional note, or accepts the variant.
7. The app calls `record_preview_feedback` with the zero-based image and variant indices.

The review surface provides:

- previous/next navigation plus image and variant selectors;
- image and annotation-overlay modes when overlay artifacts exist;
- a batch contact sheet for context;
- feedback tags from `list_feedback_tags`, with a local fallback catalog;
- `low`, `medium`, and `high` severity;
- per-variant draft retention while navigating;
- separate `Record issue` and `Accept variant` decisions;
- light/dark host theming, safe-area insets, keyboard navigation, and optional fullscreen mode.

## Server Boundary

The app does not read files directly. Every displayed image passes through the server resource template:

```text
artifact://{run_id}/{filename}
```

Before returning bytes, the server verifies that the request names one manifest-recorded PNG, resolves to the expected
run directory, matches the path recorded in the manifest, has the recorded byte size, and has the recorded SHA-256.
Traversal, unknown files, non-image artifacts, changed files, and stale manifest entries are rejected.

The source dataset remains governed by `--allowed-root`. Preview images, manifests, and feedback records remain under
`--artifact-root`. The app receives opaque artifact URIs and displays only ordinal image/variant labels and a shortened
run label. It never displays structured `path` fields.

The resource declares an empty MCP Apps CSP for connect, resource, frame, and base URI domains. The packaged app has no
remote scripts, styles, fonts, images, analytics, telemetry, or CDN assets. Host-provided theme variables and font CSS
are applied through the MCP Apps SDK and remain subject to the host sandbox.

## Feedback Contract

`Record issue` calls `record_preview_feedback` with one or more canonical tags. The selected severity is appended to
each tag, for example `too_noisy:high`. A note is trimmed and limited to 500 characters. `Accept variant` records
`accepted=true` and can be used without a negative tag.

Feedback is still validated and persisted by the Python server. The UI cannot write arbitrary files or bypass the
manifest and feedback stores. Existing tools such as `list_preview_feedback`, `adjust_pipeline`,
`compare_preview_runs`, and `export_preview_report` consume the same records.

## Host Fallback

A non-MCP-Apps host receives the unchanged tool result. Review the `contact_sheet` or `overlay_contact_sheet` artifact,
ask the user for a concrete image/variant decision, and call `record_preview_feedback` directly. Hosts that expose the
app but cannot proxy `resources/read` show an image-unavailable state; the structured tool result remains available to
the host and model.

This fallback is intentional. MCP Apps support must not be required for rendering, tuning, exporting, or automation.

## Troubleshooting

- **The UI does not open:** restart the host after upgrading and confirm it implements MCP Apps resources and tool UI
  metadata. Continue with the contact-sheet fallback if it does not.
- **The UI opens without an image:** confirm the preview run still exists under `--artifact-root`; retention cleanup or
  manual changes invalidate the resource read.
- **Overlay is disabled:** the selected variant has no annotation overlay. Supply supported bbox, keypoint, or mask
  annotations before rendering.
- **A decision cannot be saved:** confirm the run still exists and that the selected indices are present in its
  manifest. The server rejects feedback for unknown targets.
- **Fullscreen is absent:** the host did not advertise fullscreen as an available display mode.

## Verification Status

The official `@modelcontextprotocol/ext-apps` basic-host replay, exact upstream revision, reproduction commands, measured
desktop/mobile results, and evidence limits are recorded in
[MCP_APPS_BASIC_HOST_PROOF.md](MCP_APPS_BASIC_HOST_PROOF.md).

| Evidence level | Current status |
| --- | --- |
| Unit, package, stdio, and integrity checks | Automated in CI |
| Official basic-host with a generated fixture | Passed on 2026-07-13 |
| Named external host MCP Apps review | Not recorded |
| Real beta/adoption evidence for the UI | Not recorded |

Generated fixtures and basic-host runs are machine proof only. They are not beta or adoption evidence; real host and
user claims require dated reviewer records under the existing evidence process.

## Development Checks

The frontend source lives under `mcp-app/`; the generated single-file resource is committed under
`src/albumentationsx_mcp/ui/preview-review.html`.

```bash
npm --prefix mcp-app ci
npm --prefix mcp-app run test
npm --prefix mcp-app run typecheck
npm --prefix mcp-app run format:check
npm --prefix mcp-app run build
git diff --exit-code -- src/albumentationsx_mcp/ui/preview-review.html
uv build
uv run python scripts/check_mcp_app_bundle.py --dist-dir dist
```

The frontend build requires Node.js 24 for development and release automation. Node.js is not a runtime dependency of
the installed Python MCP server.
