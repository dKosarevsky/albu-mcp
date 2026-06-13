# v0.6 Candidate Ranking Design

## Goal

Make AlbumentationsX MCP better at choosing between several preview candidates by adding first-class candidate ranking,
task-aware quality profiles, and exportable tuning decision reports.

## Scope

This phase adds three bounded capabilities:

- `rank_preview_candidates`: compare one baseline preview run against multiple candidate runs and return a score-ranked
  candidate list.
- quality profiles for balanced, classification, detection, segmentation, and OCR review priorities.
- `export_tuning_report`: export the local tuning decision journal as markdown or JSON for handoff and audit.

The phase also updates docs, golden MCP evals, release metadata, and public capability descriptions. It does not add
external storage, remote image access, model training, or a UI.

## Architecture

Ranking logic belongs in a domain module, not in the FastMCP adapter. `rank_preview_candidates` should take
`PreviewRunComparison` objects, build `TuningSessionSummary` objects, and return typed ranking models. The MCP server
will only load manifests through `PreviewService`, call the ranking function, and serialize the result.

Quality profiles belong in `quality.py` because they tune interpretation of local preview metrics. Profiles expose
typed metadata through MCP so hosts can choose a task profile deliberately rather than hard-coding magic strings.

Tuning reports stay in `tuning.py` because they summarize records persisted by `TuningDecisionStore`. The report
function reads typed records and renders markdown or JSON without touching preview artifacts.

## Data Flow

1. The host renders a baseline and several candidate preview batches.
2. The host calls `rank_preview_candidates` with the baseline id, candidate ids, optional feedback tags by candidate,
   optional accepted candidate ids, and a quality profile.
3. The server compares each candidate to the baseline, builds tuning summaries, applies deterministic ranking, and
   returns the best candidate plus ranked candidates.
4. After user review, the host records accepted/rejected decisions with `record_tuning_decision`.
5. The host calls `export_tuning_report` to create a markdown or JSON decision report.

## Ranking Rules

Candidate ordering is deterministic:

1. higher `quality_score`;
2. lower `quality_risk`;
3. `export_ready` candidates before non-export-ready candidates;
4. lexical candidate run id as a stable tie-breaker.

The ranking result includes score rationale and top findings so MCP hosts can explain a recommendation without inventing
policy.

## Error Handling

Invalid run ids still fail at the existing artifact store boundary. Missing artifacts remain best-effort warnings inside
quality summaries. Empty candidate lists are rejected with a clear validation error at the server adapter. Unknown
quality profiles fall back to Pydantic validation errors rather than silent behavior changes.

## Testing

The implementation uses red-green tests:

- Unit tests for quality profile metadata and stricter profile findings.
- Unit tests for deterministic multi-candidate ranking.
- Store tests for markdown and JSON tuning reports.
- Server and stdio tests for new tool exposure.
- Golden MCP evals that render two candidates, rank them, record a decision, and list/export decisions.

## Release Shape

Feature work lands in separate commits. This is a minor release because it adds MCP tools, response models, and optional
parameters while keeping existing calls backward compatible.
