# Changelog

All notable public changes to AlbumentationsX MCP are tracked here.

## Unreleased

- Added artifact metadata to `export_tuning_session` for Markdown and JSON session handoff files.
- Added tuning session artifact links to `export_preview_report` output and response payloads.
- Clarified host acceptance coverage for automated checks versus pending manual host UI runs.

## 1.9.0 - 2026-06-18

- Added tuning session lifecycle tools: `close_tuning_session`, `archive_tuning_session`, and
  `cleanup_tuning_sessions`.
- Added interactive tuning session timelines to `export_preview_report` Markdown and HTML output.
- Added `docs/HOST_MATRIX.md` for per-host MCP acceptance checks.
- Extended golden stdio evals and contract snapshots for session lifecycle and report timeline behavior.

## 1.8.0 - 2026-06-18

- Added interactive tuning sessions with `start_tuning_session`, `record_tuning_session_step`,
  `list_tuning_sessions`, and `export_tuning_session`.
- Added a golden stdio scenario and contract snapshots for the multi-turn preview tuning flow.
- Added host acceptance and recipe guidance for session handoff, plus a reviewable demo report artifact.
- Hardened preview path handling for directories, outside-root symlinks, and failed-run cleanup.

## 1.7.1 - 2026-06-17

- Improved MCP Registry card metadata with a project homepage URL, repository ID, and PNG icons.

## 1.7.0 - 2026-06-17

- Added `albumentationsx://examples/first-preview` as an MCP-native first-preview host playbook.
- Added `run_first_preview_review` as a prompt for safe first local preview setup across MCP hosts.
- Extended golden stdio evals so the first-preview flow reads the resource and validates requests before rendering.

## 1.6.0 - 2026-06-17

- Added read-only `validate_preview_request` for schema, pipeline, path, mask, and annotation troubleshooting before
  preview rendering.
- Added representative output contract snapshots and a golden stdio scenario for preview request troubleshooting.
- Streamlined README into a concise entry point and moved release history to this changelog.

## 1.5.0 - 2026-06-15

- Added a real sample preview golden smoke that verifies the `run_host_smoke_check` template can render deterministic
  local image previews, read manifests, adjust a candidate, compare quality metrics, and clean up runs over MCP stdio.

## 1.4.0 - 2026-06-15

- Added `run_host_smoke_check` as a read-only host preflight that combines diagnostics, recipe recommendation, pipeline
  validation, and a safe preview request template.
- Added host smoke golden eval coverage through stdio and representative output snapshots for ready and blocked reports.

## 1.3.0 - 2026-06-15

- Added machine-readable `severity` to each `diagnose_environment` check.
- Added structured `remediation_actions` with stable codes, affected check codes, command hints, and diagnostics guide
  links while preserving text `next_actions`.
- Added representative output contract snapshots for healthy and missing-root diagnostics reports.

## 1.2.0 - 2026-06-15

- Added `diagnose_environment` for structured local setup diagnostics covering AlbumentationsX import/version,
  configured roots, artifact writeability, and public MCP discovery.
- Added `albumentationsx://diagnostics/guide` and `albumentationsx://examples/diagnostics` for host troubleshooting.
- Extended golden MCP evals to exercise diagnostics resources and write-probe behavior through stdio.

## 1.1.0 - 2026-06-14

- Added `albumentationsx://examples/client-smoke` as a read-only MCP host smoke playbook for capabilities, recipe
  discovery, `recommend_recipe`, and `validate_pipeline`.
- Documented the client smoke path in README, install, usage, and recipe docs.
- Updated the public MCP contract snapshot for the new compatible resource.

## 1.0.0 - 2026-06-14

- Declared the public MCP tool, resource, prompt, package metadata, and representative output contracts stable.
- Added `docs/V1_READINESS.md` with the v1 release audit for contract freeze, snapshots, golden evals, release automation,
  install flow, compatibility policy, and publication checks.
- Updated release documentation from old version-specific examples to version-neutral `vX.Y.Z` commands.
- Updated package maturity metadata to `Development Status :: 5 - Production/Stable`.

## 0.13.0 - 2026-06-14

- Added `docs/INSTALL.md` as the canonical MCP host install guide for PyPI, MCP Registry, Claude Desktop, Claude Code,
  Cursor, Codex, bounded local roots, smoke checks, and troubleshooting.
- Linked install guidance from README and usage docs so host setup is separate from workflow details.
- Added project-scaffolding tests that keep host setup docs and example snippets aligned with the published package
  command.

## 0.12.0 - 2026-06-14

- Added deterministic representative output contract snapshots for recipe recommendation, dataset scoring, preview
  feedback, and preview report exports.
- Added `scripts/export_output_contracts.py` for reviewed output fixture updates.
- Extended compatibility documentation to cover output contract snapshots alongside MCP surface snapshots.

## 0.11.0 - 2026-06-13

- Added deterministic MCP contract snapshots for tools, resources, resource templates, and prompts.
- Added `scripts/export_mcp_contract.py` for reviewed contract fixture updates.
- Added a public MCP compatibility policy covering compatible additions, breaking changes, deprecations, and required
  coverage.
- Linked compatibility guidance from README and usage docs.

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
