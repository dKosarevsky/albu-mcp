# v0.5 Quality Feedback Design

## Goal

Make AlbumentationsX MCP better at closing the preview-tuning loop by adding richer local quality signals,
annotation-retention checks, and a persisted tuning decision journal that MCP hosts can use to rank candidates.

## Scope

This phase adds three bounded capabilities:

- Image quality metrics beyond brightness/contrast/sharpness: saturation, colorfulness, entropy, clipping, and
  deterministic quality findings.
- Annotation observations recorded in preview manifests so comparisons can detect bbox, keypoint, or mask loss.
- A local tuning decision journal with MCP tools for recording acceptance/rejection and listing ranked decisions.

The phase also updates docs, golden eval coverage, release metadata, and MCP host-facing capability descriptions.
It does not introduce model training, image uploads, external telemetry, or a database service.

## Architecture

Quality scoring remains in `quality.py`. It reads preview manifests and artifacts, returns typed summaries, and
degrades through warnings rather than failing comparison when an artifact cannot be inspected.

Preview rendering records annotation observations in the existing manifest JSON. This keeps annotation quality
co-located with the preview run it describes and avoids a new persistence format for generated artifacts.

Tuning decisions live in `tuning.py` through a small `TuningDecisionStore` backed by a JSON file under the configured
artifact root. The store depends on `TuningSessionSummary`, not on FastMCP, so server tools remain thin adapters.

## Data Flow

1. `render_preview_batch` writes image artifacts, optional overlays, manifest summary, and annotation observations.
2. `compare_preview_runs` loads both manifests, compares manifest metadata, image metrics, and annotation aggregates.
3. `summarize_tuning_session` produces an agent-facing recommendation with quality findings and a score.
4. `record_tuning_decision` persists the user decision and derived summary.
5. `list_tuning_decisions` returns local history either newest-first or score-ranked.

## Error Handling

Image and annotation analysis is best-effort. Missing artifacts, malformed observation entries, and unreadable files
produce warnings in comparison output. Invalid preview run ids continue to be rejected by the artifact store boundary.
The tuning journal writes atomically enough for a local CLI/server workflow by replacing a single JSON document.

## Testing

The implementation uses red-green tests:

- Synthetic image tests for saturation, entropy, clipping, and deterministic findings.
- Preview tests for annotation observation persistence.
- Tuning store tests for record/list/ranking behavior.
- Server and stdio tests for new MCP tool exposure.
- Golden eval coverage for recording a tuning decision through MCP.

## Release Shape

Feature work lands as separate commits. This is a minor release because it adds new MCP response fields and tools while
keeping existing tools backward compatible.
