# v0.9 Review Loop And Host Examples Design

## Context

AlbumentationsX MCP already supports recommendation, preview rendering, comparison, ranking, dataset scoring, reports,
and persisted tuning decisions. The next gap is the conversational loop where a user points at a concrete preview
example, for example "example 8 is too noisy", before the host applies structured feedback tags and renders another
candidate.

## Goals

- Persist user feedback for a specific preview run, input image index, and variant index.
- Make feedback records easy for MCP hosts to list and reuse as structured feedback tags.
- Expose canonical host examples as read-only MCP resources so clients can learn the recommended loop without parsing
  prose docs.
- Extend golden evals to exercise the concrete-example feedback path through the stdio MCP server.

## Non-Goals

- No remote image access.
- No arbitrary Python execution.
- No dataset mutation.
- No UI or visual annotation editor.
- No automatic acceptance of feedback-derived candidates without a user-facing decision.

## Architecture

The new review loop is a small bounded domain next to the existing tuning journal:

- `models.py` owns strict Pydantic contracts for review feedback records, list responses, and host example resources.
- `review.py` owns a JSON-backed `PreviewFeedbackStore` under the configured artifact root.
- `server.py` remains a thin adapter. It reads the target preview manifest to validate that `image_index` and
  `variant_index` are inside the rendered run bounds, then delegates persistence to `PreviewFeedbackStore`.
- `workflows.py` owns read-only host example resources that describe canonical workflows in a machine-readable shape.
- `scripts/run_golden_evals.py` calls the new tools through MCP stdio, records the "example 8 is too noisy" path, lists it,
  and verifies the stored feedback tag can drive the next adjustment step.

## Data Contracts

`PreviewFeedbackRecord`:

- `feedback_id`: generated stable id.
- `created_at`: UTC ISO timestamp.
- `run_id`: preview run id.
- `image_index`: zero-based input image index.
- `variant_index`: zero-based variant index.
- `feedback_tags`: structured tags such as `too_noisy:high`.
- `note`: short user-facing note.
- `accepted`: whether the specific example was acceptable.
- `review_target`: one-based display label like `example 8 / variant 1`.
- `recommended_next_tool`: `adjust_pipeline` for negative feedback, `record_tuning_decision` for accepted feedback.

`PreviewFeedbackList` returns newest-first records with total count, run filter, accepted count, and aggregated feedback
tags.

`HostExample` resources describe MCP host playbooks with goal, trigger phrase, ordered tools, and success criteria.

## Error Handling

- Unknown preview runs fail through the existing manifest lookup path.
- Out-of-range `image_index` or `variant_index` raises `ValueError` with the valid bounds.
- Empty feedback tags are allowed only when `accepted=true`; negative feedback must include at least one structured tag.
- List operations clamp `limit` to `1..100`.

## Testing

- Unit tests cover feedback persistence, filtering, ranking order, aggregate tags, and validation errors.
- Server tests assert new tools and resources are registered in capabilities.
- Golden evals exercise `record_preview_feedback` and `list_preview_feedback` against the stdio server.
- Full release verification stays unchanged: pytest, ruff, format check, ty, golden evals, release-version guard, build,
  CI, PyPI, MCP Registry, and `uvx` smoke.
