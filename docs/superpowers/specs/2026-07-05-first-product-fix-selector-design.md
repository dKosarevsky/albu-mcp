# First Product Fix Selector Design

## Goal

Add a records-driven selector that chooses the first product fix only after real host evidence and beta validation gates
are green. The selector must produce an implementation packet, not modify runtime behavior or fabricate signal.

## Scope

The selector reads:

- `docs/HOST_MANUAL_RUNS.json`
- `docs/BETA_VALIDATION_RECORDS.json`
- the existing real adoption cycle gate
- beta triage/report decisions

It returns:

- gate status and blocked reasons
- a deterministic recommended fix when implementation is allowed
- a compact implementation packet with scope, tests, files, and success signal
- next commands

It does not:

- import evidence
- edit backlog records
- implement the selected product fix
- select anything when gates are blocked

## Selection Rule

When gates are blocked, return `blocked_until_external_evidence` and no selected fix.

When gates are green, choose the first beta decision ordered by:

1. `ready_for_depth_plan`
2. `candidate_backlog_item`
3. existing beta report order

Map the selected `triage_bucket` to a product fix packet:

- `host_setup_gap` -> `host_onboarding`
- `review_agent_v3_gap` -> `preview_review_agent`
- `dataset_quality_gap` -> `dataset_quality`
- `docs_gap` -> `host_docs`
- `workflow_fit_gap` -> `cv_workflow_templates`

## Command

Add:

```bash
albu-mcp activation first-product-fix --host Codex --format json
```

Default output is text. JSON and Markdown are supported.

## Output Contract

JSON includes:

- `selector_status`: `blocked_until_external_evidence`, `blocked_no_candidate`, or `ready_for_implementation`
- `implementation_allowed`
- `blocked_reasons`
- `selected_fix`
- `implementation_packet`
- `source_decisions`
- `next_commands`
- `writes_records: false`

`selected_fix` is `null` when blocked.

## Testing

Use temporary host/beta records:

- empty records keep selector blocked and no-write
- ready records select a deterministic first fix
- Markdown includes the selected product area and success signal
- CLI docs mention the new command
