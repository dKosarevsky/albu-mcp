# First-Preview Feedback

The most useful product signal is one real `render -> reject -> adjust -> accept` loop. Reporting is voluntary. No
telemetry, image upload, or background callback is built into AlbumentationsX MCP.

[Open the preview workflow feedback form](https://github.com/dKosarevsky/albu-mcp/issues/new?template=workflow-feedback.yml)
after you finish a first preview or reach a blocker.

## Copy-Ready Report

```markdown
## Goal

Task, MCP host, and what the augmentation should make robust.

## Initial render

What was useful or wrong in the first contact sheet. Use bounded tags such as `too_noisy:high`.

## Rejection

Which result you rejected and why. If the first render was acceptable, write `accepted on first render`.

## Adjustment

What you asked the host to change and which tool sequence it used.

## Outcome

Accepted result or unresolved blocker, plus the smallest product change that would have helped.

## Safe evidence (optional)

Redacted run IDs, transform names, or excerpts from `compare_preview_runs` / `export_preview_report`.
```

## Privacy Boundary

Before submitting, remove private images, absolute local paths, credentials or secrets, personal data, and proprietary
dataset details. Attach only synthetic examples or images you have intentionally made public. Prefer transform names,
feedback tags, bounded counts, and redacted report excerpts.

The issue form is the only submission step. Nothing is sent unless you deliberately open and submit the GitHub issue.
