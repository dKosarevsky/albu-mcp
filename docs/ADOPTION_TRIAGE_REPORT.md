# Adoption Triage Report

Package: `albumentationsx-mcp==1.16.0`
Telemetry policy: No automatic telemetry; use explicit GitHub issues and redacted artifacts.

## Intake Templates

- `.github/ISSUE_TEMPLATE/host-acceptance.yml`
- `.github/ISSUE_TEMPLATE/workflow-feedback.yml`
- `.github/ISSUE_TEMPLATE/dataset-health.yml`
- `.github/ISSUE_TEMPLATE/feature-request.yml`

## Manual Metrics

| Metric | Source | Measure | Response |
| --- | --- | --- | --- |
| `host_acceptance_runs` | .github/ISSUE_TEMPLATE/host-acceptance.yml | Count real host UI runs by host and status. | Update docs/HOST_MANUAL_RUNS.json only after reviewer-confirmed evidence. |
| `first_run_failures` | docs/FIRST_10_MINUTES.md and host acceptance issues | Track the last completed tool before failure. | Patch host UX packets, diagnostics guidance, or install docs. |
| `review_feedback_tags` | .github/ISSUE_TEMPLATE/workflow-feedback.yml | Group free-form feedback by interpret_preview_feedback tags and severity. | Promote repeated tags into Review Agent tests or recipe adjustments. |
| `dataset_health_findings` | .github/ISSUE_TEMPLATE/dataset-health.yml | Group reports by inspect_dataset_quality findings. | Add regression coverage for repeated findings such as dataset_unknown_category_annotations. |
| `release_response_items` | docs/RELEASE.md and docs/CHANGELOG.md | Count issues closed by docs, tests, host packets, or product code. | Link each release note to the corresponding issue class or explicit non-goal. |

## Weekly Triage

- Review new issues for private data and ask for redaction before analysis if needed.
- Assign one bucket: host setup, first-run flow, review feedback, dataset health, or feature request.
- Run interpret_preview_feedback on safe text excerpts when grouping preview review complaints.
- Convert repeated reports into tests, generated docs, or release-response notes.

## Release Checks

- `uv run python scripts/export_adoption_triage_report.py --output docs/ADOPTION_TRIAGE_REPORT.md`
- `uv run python scripts/export_public_adoption_loop.py --output docs/PUBLIC_ADOPTION_LOOP.md`
- `uv run python scripts/check_release_readiness.py`
