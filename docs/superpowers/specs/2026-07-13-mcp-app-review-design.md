# MCP Apps Preview Review Design

**Date:** 2026-07-13
**Target:** AlbumentationsX MCP v1.18.0
**Status:** Approved for implementation

## Problem

AlbumentationsX MCP already renders bounded local preview batches, contact sheets, and structured feedback records. In
text-only hosts, users must inspect artifacts outside the conversation and then describe a candidate by index. This is
functional, but it leaves unnecessary friction in the core review loop: inspect, select, tag, accept, and record.

MCP Apps is now a stable optional MCP extension. It can render the existing preview result as an interactive inline
review surface while preserving the current tool contract for hosts that do not support UI.

The v1.17.1 release also exposed an independent release-automation defect: the public Registry endpoint can take more
than the current 30-second read timeout even after metadata has been accepted. v1.18 must make that verification
observable and tolerant of the measured endpoint latency.

## Goals

1. Render results from `render_preview` and `render_preview_batch` in one interactive MCP App.
2. Let a reviewer navigate image/variant pairs, inspect one artifact, select structured feedback, and persist the result
   through the existing `record_preview_feedback` tool.
3. Keep the current structured and text tool result meaningful and unchanged for non-UI hosts.
4. Keep every image read under the configured artifact root and address artifacts by opaque `artifact://` URIs.
5. Ship a self-contained, offline-capable HTML resource with no external network domains.
6. Verify the extension through Python contracts, TypeScript tests, the official MCP Apps basic host, responsive browser
   screenshots, and a text-only stdio replay.
7. Make Registry verification tolerate the latency observed during the v1.17.1 release without hiding real metadata
   mismatches.

## Non-goals

- Replacing the existing MCP tools or changing preview generation semantics.
- Reading arbitrary local files from the app.
- Exposing dataset paths, source filenames, or image bytes to external services.
- Treating generated fixtures or automated basic-host runs as real beta/adoption evidence.
- Adding a standalone web application or remote backend.

## User Flow

1. The model calls `render_preview` or `render_preview_batch` exactly as it does today.
2. A host without MCP Apps displays the existing text and structured result.
3. A host with MCP Apps reads `ui://albumentationsx/preview-review.html` and renders the inline review surface.
4. The app receives the render tool input and result, showing only ordinal labels such as `Image 2 / Variant 3`.
5. The app reads the contact sheet and the selected image through their returned `artifact://` resource URIs.
6. The reviewer selects issue checkboxes and a severity, adds an optional note, then records feedback or accepts the
   variant.
7. The app calls the existing `record_preview_feedback` tool on the same server connection and displays the persisted
   feedback identifier and recommended next tool.

## Architecture

### Domain and storage boundary

`ArtifactStore` remains the owner of preview artifact access. A new read method accepts only a validated run ID and a
single filename, then:

- loads that run's manifest through the existing traversal-safe run lookup;
- requires an exact matching `artifact://<run-id>/<filename>` entry;
- permits only preview image kinds with `image/png` MIME type;
- resolves the file under the expected run directory, not from untrusted caller input;
- verifies the recorded size and SHA-256 digest before returning bytes.

This method is the only new filesystem read path.

### MCP adapter

A focused `mcp_app.py` adapter owns MCP Apps constants, metadata, packaged HTML loading, and resource registration. It
registers:

- `ui://albumentationsx/preview-review.html` with MIME type `text/html;profile=mcp-app` and a deny-by-default CSP;
- `artifact://{run_id}/{filename}` as an `image/png` resource template backed by `ArtifactStore`.

The existing render decorators receive modern nested metadata:

```json
{
  "ui": {
    "resourceUri": "ui://albumentationsx/preview-review.html",
    "visibility": ["model", "app"]
  }
}
```

No deprecated flat metadata key is emitted. Registration remains unconditional because the Python FastMCP server is
constructed before a per-client capability is available and may serve multiple clients. This is safe progressive
enhancement: old hosts ignore unknown metadata, while both render tools continue to return their normal fallback.

### View application

`mcp-app/` is a small Vanilla TypeScript workspace. It uses the official `@modelcontextprotocol/ext-apps` SDK,
`lucide` icons, Vite, and `vite-plugin-singlefile`. The build output is one committed packaged file:

`src/albumentationsx_mcp/ui/preview-review.html`

The source and generated artifact are both versioned. CI rebuilds the app and fails on drift. Python package builds do
not require Node and always contain the reviewed generated asset.

The view registers all SDK handlers before `connect()`, applies host theme/style/safe-area context, and revokes object
URLs when images change or the app tears down. It never renders local path fields from the structured result.

### UI composition

The review surface is a compact work UI rather than a landing page:

- top status bar: run state, item count, and optional fullscreen control;
- main visual area: contact sheet overview and a stable selected-image viewport;
- navigation: previous/next controls plus image and variant selectors;
- feedback area: issue checkboxes, low/medium/high severity segmented control, note field, record action, and accept
  action;
- explicit loading, empty, error, saving, and saved states.

The layout becomes a single column on narrow hosts and a visual/review split on wider hosts. Host CSS variables are
used with neutral fallbacks; no external fonts, images, scripts, analytics, or fetch calls are allowed.

## Compatibility and fallback

- Render tool names, input schemas, and Python return models remain unchanged.
- FastMCP continues to produce structured content plus text content from the existing dictionary result.
- Hosts that ignore `_meta.ui` retain the exact pre-v1.18 behavior.
- The artifact resource is additive and read-only.
- App calls reuse `record_preview_feedback`; there is no second feedback persistence path.

## Testing strategy

1. TDD unit tests for artifact URI validation, manifest membership, path containment, size/digest integrity, and image
   kind restrictions.
2. MCP contract tests for modern tool metadata, app resource MIME/CSP, packaged single-file HTML, resource discovery,
   and binary resource reads over stdio.
3. TypeScript unit tests for artifact ordering, image/variant indexing, feedback-tag severity composition, and private
   path omission.
4. Frontend typecheck, formatting, deterministic single-file build, and generated-asset drift guard.
5. Official MCP Apps basic-host replay with a generated local fixture, Playwright screenshots at desktop and mobile
   widths, interaction checks, and nonblank image-pixel verification.
6. Existing stdio golden evaluations and full Python quality gates to prove text-only fallback stability.
7. A release verifier test proving transient Registry timeouts retry while semantic mismatches still fail.

## Evidence policy

Automated and generated-fixture runs are machine verification only. The release documentation will record them as such.
A real beta signal requires an actual external reviewer using their own image or dataset and providing attributable
feedback; v1.18 readiness must not fabricate that evidence.
