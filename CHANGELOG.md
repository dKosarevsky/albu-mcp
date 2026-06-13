# Changelog

All notable public changes to AlbumentationsX MCP are tracked here.

## Unreleased

- No unreleased changes yet.

## 0.10.0 - 2026-06-13

- Added concrete preview feedback records to Markdown and HTML preview reports.
- Wired `export_preview_report` to include matching `record_preview_feedback` entries for baseline and candidate runs.
- Extended golden MCP evals to verify feedback-aware preview report content through stdio.
- Documented v1 readiness criteria around stable MCP contracts, schema snapshots, and compatibility policy.

## 0.9.0 - 2026-06-13

- Added `record_preview_feedback` and `list_preview_feedback` for concrete image/variant feedback such as
  "example 8 is too noisy".
- Added host example resources for the preview feedback loop and visual report handoff.
- Extended golden MCP evals to persist concrete preview feedback and reuse aggregated tags for adjustment.
- Documented the concrete preview feedback workflow in README, usage docs, and recipes.

## 0.8.0 - 2026-06-13

- Added deterministic preview report snapshot fixtures with tiny real PNG contact sheets.
- Added Markdown image references and HTML thumbnails to preview reports.
- Added structured `recommend_recipe` explanations for quality profiles, targets, feedback tags, and workflow tools.
- Extended golden MCP evals to verify recipe explanations and preview report image markup.

## 0.7.0 - 2026-06-13

- Added `recommend_recipe` for task-aware starter pipelines, quality profiles, feedback tags, and next-tool guidance.
- Added `score_dataset_preview_candidates` for dataset-level scoring across multiple candidate preview runs.
- Added `export_preview_report` for Markdown or HTML visual reports with contact sheets, ranking, metrics, and decisions.
- Exposed `albumentationsx://recipes/catalog` for MCP host discovery.
- Extended golden MCP evals to cover recipe recommendation, dataset scoring, and preview report export.

## 0.6.0 - 2026-06-13

- Added task-aware quality profiles for balanced, classification, detection, segmentation, and OCR review.
- Added `rank_preview_candidates` for deterministic multi-candidate preview ranking.
- Added `export_tuning_report` for Markdown or JSON tuning decision handoff.
- Exposed `albumentationsx://quality-profiles` for MCP host discovery.
- Extended golden MCP evals to cover two-candidate ranking and report export.

## 0.5.0 - 2026-06-13

- Added richer local quality metrics: saturation, colorfulness, entropy, clipping, and deterministic quality findings.
- Added annotation retention observations for bbox, keypoint, and mask previews.
- Added annotation-aware comparison summaries and findings in `compare_preview_runs`.
- Added `quality_score`, `quality_risk`, and structured findings to `summarize_tuning_session`.
- Added `record_tuning_decision` and `list_tuning_decisions` for a local JSON-backed tuning decision journal.
- Extended golden MCP evals to cover persisted tuning decisions.

## 0.4.0 - 2026-06-13

- Added local image quality metrics to preview run comparisons.
- Added `summarize_tuning_session` for baseline-to-candidate feedback, quality deltas, and export readiness.
- Added task workflow profiles and host recipes for classification, detection, segmentation, and OCR sessions.
- Added a golden MCP scenario covering quality summaries and tuning session summaries.

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
