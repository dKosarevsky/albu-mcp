# Growth Conversion Sprint Design

**Date:** 2026-07-14
**Status:** Approved for implementation

## Problem

Raw PyPI downloads are a weak adoption signal for AlbumentationsX MCP. The launch month included 35 releases, package
mirrors download every distribution, and repository automation produces clone traffic. At the same time, the public
README has become an operator index: the actual preview result is not visible above the fold, Claude Desktop requires a
multi-step trip through GitHub Releases, and the documentation section exposes internal evidence machinery before a new
user reaches a first preview.

The product already has the necessary runtime, official Albumentations documentation, Registry distribution, a Claude
Desktop bundle, and deterministic demo artifacts. This sprint should improve discovery and conversion without changing
the MCP tool contract or collecting private usage data.

## Goals

1. Turn the README into a short path from value proposition to install, preview, and trusted documentation.
2. Give Claude Desktop users a stable `releases/latest/download/albumentationsx-mcp.mcpb` URL.
3. Measure release-independent demand with aggregate PyPI, GitHub Traffic, and release-asset data.
4. Provide reusable, targeted launch copy for classification robustness, detection, and segmentation users.
5. Keep human-only outreach explicit; automation must not post to third-party communities or impersonate Albumentations.

## Non-goals

- Adding runtime telemetry, analytics SDKs, cookies, identifiers, or network calls to the MCP server.
- Increasing downloads through release spam, mirrors, synthetic installs, or dependency injection.
- Changing preview generation, host configuration, filesystem permissions, or the public MCP surface.
- Publishing social posts or upstream announcements without a human account owner.
- Treating PyPI downloads as proof of a successful first preview.

## Architecture

### Public conversion surface

`README.md` becomes the primary product funnel. It keeps the required AlbumentationsX link and package badges, then
shows a genuine generated comparison artifact, a portable `uvx` command, a direct Claude Desktop bundle link, one first
preview prompt, concise capabilities, safety guarantees, and a curated documentation list. `docs/INDEX.md` becomes the
maintainer-facing navigation boundary for deeper operational documents.

### Stable desktop artifact

The release workflow keeps the versioned MCPB artifact and creates a byte-identical `albumentationsx-mcp.mcpb` alias
before checksums are written. Both files remain outside PyPI and are uploaded to the same GitHub Release. The stable
name makes GitHub's `releases/latest/download/...` URL valid while preserving versioned reproducibility.

### Aggregate growth report

`albumentationsx_mcp.growth` is a pure analysis module. It accepts already-fetched PyPI daily data, GitHub releases,
GitHub Traffic aggregates, referrers, and repository metadata. It computes current and previous seven-day totals,
week-over-week change, a 28-day median excluding release days plus the following two calendar days, MCPB downloads,
human page reach, and top referrers.

`scripts/export_growth_report.py` is the network adapter. It fetches public PyPI and GitHub data, optionally uses
`GH_TOKEN` or `GITHUB_TOKEN` for owner-only Traffic endpoints, and supports an offline JSON input for deterministic
reproduction. The output contains only aggregate counts and source status. It never reads datasets, MCP artifacts,
host logs, or local paths.

### Launch packet

`docs/GROWTH.md` defines the metric policy and operating cadence. `docs/LAUNCH_KIT.md` receives three concrete campaign
cards with a single problem, prompt, artifact, destination URL, and success signal each. External publication remains a
manual checklist item.

## Error handling

- Missing GitHub Traffic authorization produces an explicit unavailable source, not a zero count.
- Invalid or empty PyPI daily data fails the report because download windows would be misleading.
- Malformed dates, negative counts, and unsupported payload shapes fail with actionable messages.
- A zero previous-week total reports an undefined percentage instead of dividing by zero.
- Offline input uses the same validation and analysis path as live data.

## Testing

1. Contract tests keep the README concise, visual, and linked to the stable MCPB URL and curated docs index.
2. Workflow tests require both versioned and stable MCPB assets before checksum generation and prohibit MCPB upload to
   PyPI.
3. Parameterized unit tests cover release-window exclusion, weekly comparison, zero denominators, aggregate GitHub
   metrics, and MCPB asset counts.
4. CLI tests use offline fixtures and prove Markdown and JSON output without network access.
5. Full pytest, Ruff, formatting, ty, release readiness, package build, and MCPB validation remain the completion gate.

## Success criteria

- README is no more than 100 lines and links to no more than ten primary documentation destinations.
- The latest GitHub Release exposes both versioned and stable MCPB names after the next release.
- A maintainer can generate an aggregate report with one command and no runtime telemetry.
- Launch materials contain three audience-specific campaigns and clearly separate automated preparation from manual
  publication.
