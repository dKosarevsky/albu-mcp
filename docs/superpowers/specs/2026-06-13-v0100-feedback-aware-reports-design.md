# v0.10 Feedback-Aware Preview Reports Design

## Context

Version 0.9 added a concrete preview feedback journal for records such as "example 8 is too noisy". Preview reports still
show ranking, metrics, contact sheets, and tuning decisions, but they do not yet include those concrete user notes. That
leaves final handoff reports missing the most useful conversational context.

## Goals

- Include matching `PreviewFeedbackRecord` entries in Markdown and HTML preview reports.
- Keep report rendering pure: `PreviewReportService` receives feedback records from the caller and does not read stores.
- Have `server.py` collect feedback for baseline and candidate run ids from `PreviewFeedbackStore` when exporting a report.
- Extend golden evals so the stdio MCP path records concrete feedback and confirms the exported report contains it.
- Prepare the project for a later v1 stability release by making the full preview tuning loop visible in reports.

## Non-Goals

- No changes to the preview feedback storage format.
- No automatic feedback-based candidate acceptance.
- No migration tooling; records are additive and optional.
- No schema-breaking changes to existing report fields.

## Architecture

`reports.py` adds an optional `feedback_records` parameter to `PreviewReportService.export_report`. Markdown and HTML
renderers add a "Concrete Preview Feedback" section after tuning decisions. If no records are supplied, the report says
no concrete feedback matched the report.

`server.py` remains the integration layer. It already owns `PreviewFeedbackStore`, so `export_preview_report` can list
feedback for the baseline and bounded candidate run ids, then pass the matching records into `PreviewReportService`.

Golden evals use the v0.9 feedback path, then verify `export_preview_report` content includes the concrete note and tag.

## v1 Criteria

After v0.10, the project has the core loop needed for v1: discovery, validation, preview, comparison, concrete feedback,
ranking, decisions, reports, export, PyPI, Registry, and golden evals. A v1 release should be a contract-stability pass:

- freeze public tool/resource names and major response fields;
- add a concise compatibility policy;
- add schema snapshot checks for MCP-facing contracts;
- verify README/USAGE describe the final v1 workflow.
