# Changelog

All notable public changes to AlbumentationsX MCP are tracked here.

## Unreleased

- No unreleased changes yet.

## 0.3.0 - 2026-06-13

- Added feedback severity modifiers for `adjust_pipeline`: `:low`, `:medium`, and `:high`.
- Added `suggested_feedback_tags` to `compare_preview_runs` so agents can present review candidates before asking the
  user for final feedback.
- Documented that compare-run suggestions are not automatic quality verdicts and should be confirmed against contact
  sheets.

## 0.2.1 - 2026-06-13

- Added a generated demo workflow for reviewable preview batches and side-by-side comparison contact sheets.
- Documented the public MCP workflow from conservative recommendation through `compare_preview_runs` and export.
- Polished release notes and public discovery documentation for the PyPI plus MCP Registry distribution model.

## 0.2.0 - 2026-06-13

- Added batch preview rendering with contact sheets for multi-image robustness review.
- Added preview manifest comparison through `compare_preview_runs`.
- Added preview run listing, manifest lookup, deletion, and retention cleanup tools.
- Hardened release automation with version checks, post-release smoke tests, and MCP Registry publishing.

## 0.1.0 - 2026-06-13

- Published the initial installable MCP stdio server package.
- Added transform search, schema inspection, validation, pipeline recommendation, adjustment, explanation, preview rendering,
  and export tools.
- Added typed schemas, bounded local artifact handling, core documentation, examples, CI, and golden MCP evals.
