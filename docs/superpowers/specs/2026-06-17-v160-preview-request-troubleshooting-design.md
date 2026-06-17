# v1.6 Preview Request Troubleshooting Design

## Context

`run_host_smoke_check` proves that a host is connected and returns a safe `render_preview_batch` template. `v1.5` proves
that the happy-path template can render deterministic sample previews over MCP stdio. The remaining gap is the first
class of real user failures: the template is filled with a missing image path, a path outside `--allowed-root`, a bad
mask path, or mismatched annotations. Today those failures surface from `render_preview_batch` as tool errors rather
than an agent-legible remediation report.

## Goal

Add a read-only `validate_preview_request` MCP tool that validates a preview request before rendering. It must report
schema, pipeline, input path, mask path, and annotation-count problems with stable check codes, severity, next actions,
and remediation actions.

## Options Considered

1. Improve `render_preview_batch` exceptions only.
   This keeps the tool surface smaller, but MCP hosts still have to trigger the expensive render path to learn that a
   path is wrong.

2. Add a separate read-only validator tool.
   This gives hosts an explicit preflight between `run_host_smoke_check` and `render_preview_batch`, preserves renderer
   behavior, and creates a stable output contract for troubleshooting.

3. Fold request validation into `run_host_smoke_check`.
   This does not fit because host smoke intentionally avoids user image paths and cannot validate a filled request.

Chosen approach: option 2.

## Architecture

Create `src/albumentationsx_mcp/preview_validation.py` with pure typed report models and a `PreviewRequestValidator`.
The validator depends on `PipelineService` and `PathPolicy`, but it does not render images and does not write files. The
MCP adapter in `server.py` only parses arguments and delegates to the validator.

The report mirrors the diagnostics style without reusing environment-specific models directly:

- `status`: `ok`, `warning`, or `error`;
- `valid`: boolean shortcut for `status == "ok"`;
- `checks`: ordered check list with `code`, `status`, `severity`, `message`, and `details`;
- `warnings`: warning/error messages for quick host display;
- `next_actions`: human-readable next steps;
- `remediation_actions`: stable action codes for automation;
- `normalized_request`: request JSON when schema validation succeeds.

## Check Codes

- `preview_request_schema_valid`
- `preview_request_schema_invalid`
- `pipeline_valid`
- `pipeline_invalid`
- `input_path_accessible`
- `input_path_missing`
- `input_path_not_file`
- `input_path_outside_allowed_root`
- `mask_path_accessible`
- `mask_path_missing`
- `mask_path_not_file`
- `mask_path_outside_allowed_root`
- `annotation_count_matches`
- `annotation_count_mismatch`

## Error Handling

Schema errors should stop deeper checks because there is no reliable request shape. Pipeline errors should be reported
alongside path checks when request parsing succeeds. Path checks should prefer `outside_allowed_root` over `missing` when
the path is outside every allowed root, even if that outside path also does not exist. The tool should never read image
bytes; existence, file type, and root membership are enough.

## Testing

Use TDD:

1. Unit tests for missing input, outside-root input, annotation mismatch, mask path errors, and a valid request.
2. Server tests for public tool registration and capabilities.
3. MCP contract snapshot update for the new tool.
4. Output contract snapshots for representative valid, missing input, and outside-root reports.
5. Golden eval coverage that calls `validate_preview_request` over stdio before rendering and verifies missing-path
   remediation over stdio.

## Release

This is a compatible public MCP tool addition and should ship as `v1.6.0` with docs, changelog, package metadata, PyPI,
GitHub Release, and MCP Registry metadata updates.
