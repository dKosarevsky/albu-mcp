# Classification Robustness Activation Sprint Design

## Problem

AlbumentationsX MCP has a published package, a stable MCPB download, official Albumentations documentation, a concise
README, and a voluntary workflow-feedback form. Those surfaces are not yet connected into a measurable activation
funnel. As of 2026-08-12, the repository had 3 unique visitors in GitHub's rolling 14-day window, 22 MCPB downloads
across all releases, 1 MCPB download on the latest release, and no public workflow-feedback issues. PyPI reported 121
downloads during the latest seven-day period, but the comparison period was incomplete.

Adding more MCP tools would not address the current evidence gap. The next iteration must attract qualified users and
help them complete one real `render -> reject -> adjust -> accept` workflow without introducing runtime telemetry.

## Goals

1. Publish one canonical classification-robustness use case with a copyable install and host prompt.
2. Collect three voluntary, completed adjustment loops from real users during a bounded 14-day campaign.
3. Raise qualified repository reach to at least 20 unique visitors in GitHub's rolling 14-day window.
4. Add at least five MCPB downloads across releases relative to the campaign baseline.
5. Produce a reproducible, privacy-safe activation report from aggregate public metrics and voluntary GitHub issues.

## Non-Goals

- Adding a new runtime MCP tool or changing an existing MCP contract.
- Collecting automatic runtime events, image contents, local paths, host logs, or machine identifiers.
- Treating PyPI downloads as proof of successful use.
- Manufacturing installs, publishing repeated releases to inflate downloads, or automating posts to third-party
  communities without an authenticated human account.
- Claiming a causal campaign effect when source or timing evidence is missing.

## User Flow

The campaign has one primary destination: a repository use-case page for classification robustness. A user sees the
before/after contact sheet, chooses MCPB or `uvx`, runs the host smoke check, executes `run_first_preview`, rejects an
excessive variant, asks for an adjustment, accepts the new result, and optionally opens the workflow-feedback form.
The official Albumentations MCP guide remains linked from the use-case page as the upstream trust source.

The use-case page is intentionally executable rather than promotional. It has one prompt, bounded acceptance criteria,
the expected artifact, a troubleshooting path, and a privacy-safe feedback call to action.

## Architecture

### Public Delivery

`docs/use-cases/CLASSIFICATION_ROBUSTNESS.md` is the canonical campaign destination. `README.md` and `docs/INDEX.md`
link to it without expanding the README beyond its concise product funnel. `scripts/export_launch_kit.py` remains the
single source for channel-ready copy and emits Discord, X, and generic community variants that point to the same page.

### Voluntary Attribution

`.github/ISSUE_TEMPLATE/workflow-feedback.yml` gains structured fields for campaign/use case, discovery source,
install route, and workflow outcome. The campaign and outcome are required; source and install route include an
explicit unknown/not-sure choice. A completed campaign loop is counted only when the submitted outcome is
`accepted-after-adjustment`. Existing issues without the new fields remain valid but are not attributed retroactively.

### Domain Analysis

`albumentationsx_mcp.campaign_activation` is a pure module. It accepts an already-built growth report, a campaign
configuration, and GitHub issue-shaped mappings. It validates bounded campaign dates and targets, extracts issue-form
fields, limits reports to public `created_at` timestamps inside the observed campaign window, deduplicates public
submitters in memory, and returns aggregate counts only. Publication timestamps outside the campaign window are
rejected, while future publications relative to `as_of` do not activate attribution. The module never performs network
access or returns issue bodies, titles, URLs, usernames, issue timestamps, images, or local paths.

The report distinguishes three evidence classes:

- Qualified reach: GitHub's rolling 14-day unique visitors, an aggregate directional measure.
- Distribution conversion proxy: incremental MCPB downloads across releases from a fixed baseline.
- Product activation: voluntary `accepted-after-adjustment` reports for the campaign, including an aggregate count of
  distinct submitters.

PyPI demand remains contextual and inherits completeness warnings from the growth report.

### Network Adapter

`scripts/export_campaign_activation_report.py` owns live HTTP access and offline fixture loading. It reuses the existing
growth-report adapter, fetches public workflow-feedback issues with GitHub pagination, and passes only fetched values to
the pure domain module. Markdown and JSON outputs contain aggregate metrics and warnings. Offline inputs make every
decision reproducible in tests.

### Campaign Record

`docs/campaigns/classification-robustness-2026-08.json` records the fixed campaign ID, 14-day dates, public destination,
baseline metrics, and targets. The baseline is the privacy-safe report collected before publication. Publication URLs
and timestamps must be real; absent external posts remain explicitly unreported.

## Decision Policy

Before the deadline, the report recommends `continue` and names the largest unmet stage. At or after the deadline:

- `continue` when all three targets are met;
- `adjust` when there is reach or MCPB movement but the full activation target is missed;
- `stop` when reach, MCPB downloads, and completed loops all show no movement from baseline.

The recommendation is descriptive. It never attributes a metric change to a channel unless a voluntary discovery
field or recorded publication URL supports that statement.

## Release Strategy

The implementation is a patch release because the MCP protocol and tool surface remain unchanged. The release updates
the PyPI README, publishes the canonical use case through the repository, resets the stable latest MCPB destination to
the new release, and supplies an owned-channel release URL for the campaign record. Release-window PyPI downloads stay
excluded from demand interpretation.

## Testing

- Documentation contract tests prove one canonical destination, one prompt, explicit acceptance criteria, and a
  privacy-safe feedback link.
- YAML tests prove the structured feedback options and required campaign outcome.
- Parameterized domain tests cover successful, blocked, duplicate-submitter, unattributed, pre-deadline, and
  post-deadline reports.
- CLI tests use synthetic offline fixtures and verify Markdown/JSON output contains no issue-level identifiers.
- Pagination tests prove all matching GitHub issues are fetched.
- Full pytest, Ruff, formatting, ty, release readiness, package build, and MCPB validation remain the release gate.

## Success Criteria

- The canonical use-case page is linked from README, docs index, launch copy, and release notes.
- The voluntary form can distinguish campaign, channel, install route, and accepted-after-adjustment outcome.
- A maintainer can regenerate a privacy-safe campaign report with one command or deterministic offline inputs.
- The committed baseline and targets are explicit and machine-readable.
- No new runtime telemetry, network behavior, or MCP tool is introduced.
