# Product Fix Implementation Plan Design

## Goal

Add a report-only activation command that turns the selected first product fix into a concrete TDD implementation plan.

## Command

```bash
albu-mcp activation product-fix-implementation-plan --host Codex --format json
albu-mcp activation product-fix-implementation-plan --host Codex --output-dir docs/product-fix-implementation-plan --format markdown
```

## Scope

The command reads the same real adoption inputs as `activation first-product-fix`:

- `docs/HOST_MANUAL_RUNS.json`
- `docs/BETA_VALIDATION_RECORDS.json`
- selector status, selected fix, and implementation packet

It never writes host evidence, beta records, backlog files, runtime product code, branches, tags, or releases. With
`--output-dir`, it writes generated operator artifacts only.

## Behavior

When the selector is blocked, return:

- `plan_status`: `blocked_until_first_product_fix`
- `implementation_allowed`: `false`
- copied selector `blocked_reasons`
- no `implementation_plan`
- next commands to collect real evidence and rerun the selector

When the selector is ready, return:

- `plan_status`: `ready_for_tdd`
- `implementation_allowed`: `true`
- selected product area, triage bucket, scope, success signal
- phase cards for RED tests, minimal implementation, verification, PR/merge
- expected files from the selector implementation packet

## Artifact Pack

For Markdown or JSON output, write:

- `product-fix-implementation-plan-index.md/json`
- `tdd-plan.md/json`
- `verification-plan.md/json`

The Markdown pack is operator-facing. The JSON pack is automation-facing.

## Architecture

Create `src/albumentationsx_mcp/product_fix_implementation_plan.py`. It depends on
`first_product_fix_selector.py` and exposes pure builder/render functions. `cli.py` only parses args, calls the builder,
formats output, and writes artifacts.

## Testing

Add CLI tests with temporary host/beta records:

- empty records keep the plan blocked and no-write
- ready records produce a deterministic `preview_review_agent` TDD plan
- `--output-dir --format markdown` writes three artifacts
- host and beta records remain unchanged

