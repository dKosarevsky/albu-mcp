# Next MCP Development Design

## Goal

Improve AlbumentationsX MCP beyond manifest-only preview comparison by adding lightweight quality signals, persistent
tuning context, richer workflow recipes, and eval coverage while preserving local-only, typed, deterministic behavior.

## Scope

This phase adds four bounded capabilities:

- Quality-aware preview comparison based on local preview artifacts already written by the server.
- Tuning session summaries that help an MCP host explain how a baseline became an accepted candidate.
- Task profile guidance for classification, detection, segmentation, OCR, and annotation review.
- Documentation and eval scenarios that keep the public contract discoverable through MCP resources and host examples.

This phase does not train models, upload images, fetch remote assets, or introduce non-local telemetry.

## Architecture

Quality analysis stays outside the MCP adapter. A new pure-ish domain module reads local artifact paths and returns typed
metrics with graceful degradation when files are missing or unsupported. `PreviewService` remains the application service:
it reads manifests, asks the analyzer for optional metrics, and returns enriched comparison models.

Tuning history is derived from manifests and comparison output. The first implementation should be summary-oriented, not
a database: no new persistence format beyond recorded manifests unless a test proves it is necessary.

Workflow recipes remain machine-readable resources in `workflows.py` and human-readable documentation in `docs/USAGE.md`.
Golden evals exercise the MCP surface so host-facing behavior does not drift.

## Error Handling

Image metric collection is best-effort. Missing artifacts, unreadable files, or size mismatches should produce warnings
in the comparison result, not fail the whole `compare_preview_runs` call. Validation and path allowlists remain enforced
by existing preview rendering and artifact store boundaries.

## Testing

Each behavior is added with red-green tests:

- Unit tests for image metric functions using synthetic PIL images.
- Service tests proving recorded preview runs include comparison quality summaries.
- Workflow/docs tests for new resources and host-facing text.
- Golden MCP eval updates for the public tool contract.

## Release Shape

Feature work lands in separate commits. A minor release is appropriate once quality-aware comparison and tuning summaries
are both exposed through the MCP API. Docs-only or CI-only changes do not need tags.
