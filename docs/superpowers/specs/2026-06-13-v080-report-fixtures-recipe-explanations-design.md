# v0.8 Report Fixtures And Recipe Explanations Design

## Goal

Improve confidence and usability around the new v0.7 reporting and recipe features. Reports should be regression-tested with realistic tiny image fixtures and snapshot-style assertions, and recipes should explain why a host should choose a profile, targets, feedback tags, and next tools.

## Scope

This release keeps the current architecture and adds two focused improvements:

- richer preview report rendering with image references, tested through deterministic Markdown and HTML snapshots;
- richer `recommend_recipe` output that gives MCP hosts structured reasoning for profile choice, targets, feedback tags, and workflow tools.

No new transport, storage backend, external image service, browser rendering, or machine-learning model is added.

## Architecture

Report rendering remains in `reports.py`. Tests create tiny real PNG contact sheets in temporary directories, render Markdown and HTML reports, normalize dynamic paths, and compare the important output against checked-in text snapshots. The report service will render Markdown image references and HTML thumbnails for contact sheets while keeping local `file://` links.

Recipe advice remains in `recipes.py`. The Pydantic contract gains a small `RecipeExplanation` model and `RecipeRecommendation.explanations`. The server continues to call `recommend_recipe` as a thin adapter.

## Report Snapshot Testing

The snapshot tests use a test-only fixture builder that:

- writes real 8x8 PNG contact sheets with Pillow;
- builds baseline and two candidate manifests;
- builds a dataset score through the public scorer;
- records a representative accepted tuning decision;
- exports Markdown and HTML reports through `PreviewReportService`.

Before comparing snapshots, tests normalize temporary filesystem paths and generated report artifact filenames. This keeps snapshots stable without hiding real file-path behavior.

## Recipe Explanations

Each recommendation returns structured explanation records:

- `quality_profile`: why this profile was selected;
- `targets`: why default or explicit targets are used;
- `feedback_tags`: why these tags should be offered first;
- `workflow`: why the recommended tools are ordered this way.

This remains deterministic and task-local. Unknown tasks keep the balanced fallback with a clear fallback explanation.

## Testing

New tests are TDD-first:

- `tests/test_report_snapshots.py` verifies Markdown and HTML snapshots using real tiny PNG contact sheet fixtures.
- `tests/test_recipes.py` verifies structured explanations for matched and fallback recipes.
- Existing server, stdio, golden eval, and release tests remain the integration safety net.
