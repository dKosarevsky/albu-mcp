# v0.12 Output Contract Snapshots Design

## Context

`v0.11.0` added contract snapshots for the public MCP surface: tools, resources, resource templates, and prompts. That
guards names and input schemas, but it does not lock representative response shapes. Before considering any v1 release,
the project needs a second guardrail for high-value output contracts that MCP hosts are likely to consume directly.

## Goals

- Add deterministic snapshots for representative output payloads.
- Cover the workflow outputs most likely to be consumed by hosts: recipe recommendation, dataset candidate scoring,
  preview feedback records/lists, and preview report export metadata/content shape.
- Keep output snapshot generation as development tooling in `scripts/`, not runtime server behavior.
- Normalize unstable values such as temporary paths, artifact hashes, generated ids, timestamps, and report UUIDs.
- Release this as `v0.12.0` if verification and publication checks pass.

## Non-Goals

- No new MCP tools, resources, prompts, or response fields.
- No exhaustive snapshot for every tool response.
- No binary preview artifact snapshots.
- No major-version contract freeze.

## Architecture

Create `scripts/export_output_contracts.py` as the single output snapshot exporter. It builds representative outputs by
calling existing domain services and models directly:

- `recommend_recipe(task="ocr", intensity="low")`;
- `score_dataset_preview_candidates` using deterministic in-memory `PreviewRunComparison` objects;
- `PreviewFeedbackStore.record_feedback` and `list_feedback` with normalized ids and timestamps;
- `PreviewReportService.export_report` with deterministic manifests and normalized report artifact metadata.

The exporter writes canonical JSON with sorted keys and a trailing newline. `tests/test_output_contract_snapshots.py`
compares current generated output against `tests/fixtures/snapshots/output_contracts.json` and verifies the fixture is
canonical. If output shape changes intentionally, the fixture update must be committed with changelog/docs explaining the
contract change.

## Verification

The release is valid only if the output snapshot test, full pytest suite, ruff, format check, ty, golden evals, release
version guard, build, CI, PyPI smoke, and MCP Registry publish all pass.
