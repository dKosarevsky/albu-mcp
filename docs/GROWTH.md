# Aggregate Growth Measurement

Use the growth report to separate qualified demand from release, mirror, CI, and indexing traffic. It is a maintainer
tool, not a product analytics client.

## Privacy Boundary

No runtime telemetry is added to the MCP server. The report reads aggregate PyPI and GitHub API responses only. It does
not inspect image datasets, preview artifacts, host logs, prompts, local paths, or user identifiers.

GitHub Traffic endpoints are owner-only. Without an authenticated token, the report marks views and referrers as
unavailable instead of recording false zeroes. Tokens are used as request headers and are never written to output.

## Generate A Report

Public sources only:

```bash
uv run python scripts/export_growth_report.py --output /tmp/albu-growth.md
```

Include owner-only GitHub views and referrers:

```bash
GH_TOKEN="$(gh auth token)" uv run python scripts/export_growth_report.py --output /tmp/albu-growth.md
```

Produce structured output:

```bash
GH_TOKEN="$(gh auth token)" uv run python scripts/export_growth_report.py --format json --output /tmp/albu-growth.json
```

Reproduce the analyzer without network access:

```bash
uv run python scripts/export_growth_report.py \
  --input tests/fixtures/growth_report_input.json \
  --output /tmp/albu-growth-fixture.md
```

Live reports are dated operational artifacts; write them outside the repository unless a specific evidence review
requires a sanitized snapshot.

## Metric Policy

- `last_7_days` and `previous_7_days` use PyPI downloads without mirrors.
- `week_over_week_percent` is undefined when the previous period is zero.
- The default baseline uses 28 calendar days and excludes each release day plus the following two calendar days.
- Missing dates make a weekly window incomplete; the report does not silently claim completeness.
- GitHub views, unique visitors, and referrers are aggregate owner metrics.
- MCPB counts include every `.mcpb` asset, including stable and versioned filenames.

The release-excluded median is the primary PyPI trend. Do not optimize raw downloads with extra releases, artificial
installs, mirrors, or unrelated dependencies.

## Weekly Cadence

1. Generate the report on the same weekday.
2. Review the release-excluded median before the raw weekly total.
3. Check qualified GitHub reach and top referrers.
4. Check stable and versioned MCPB downloads.
5. Compare external feedback and voluntary evidence of a successful first preview.
6. Choose one acquisition or conversion experiment and keep its destination and success signal fixed for one week.

PyPI downloads remain a distribution proxy. A successful first preview, useful reviewer feedback, and repeat use are
stronger product signals; collect them through explicit, voluntary host evidence or GitHub feedback, not hidden
telemetry.
