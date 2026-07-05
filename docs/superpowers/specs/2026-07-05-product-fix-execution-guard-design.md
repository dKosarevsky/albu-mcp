# Product Fix Execution Guard Design

## Goal

Add a report-only activation command that turns a ready product-fix implementation plan into a guarded execution handoff. The command must make it clear whether implementation may start, which branch name is expected, which commands should be run first, and which files form the allowed scope.

## Architecture

The feature is a thin orchestration layer over `product_fix_implementation_plan`.

- `product_fix_execution_guard.py` owns the domain contract and artifact rendering.
- `cli.py` only parses arguments, delegates to the domain module, and writes optional artifacts.
- Existing selector and implementation-plan modules remain unchanged and continue to own evidence gating and TDD plan construction.

The guard does not execute git commands, write evidence records, or mutate source files. It produces a deterministic handoff that another operator or agent can execute.

## Behavior

When `product-fix-implementation-plan` is blocked, the guard returns:

- `guard_status: blocked_until_tdd_plan`
- `execution_allowed: false`
- no branch scaffold
- copied blocked reasons and next commands from the plan layer

When a plan is ready, the guard returns:

- `guard_status: ready_for_branch_scaffold`
- `execution_allowed: true`
- a deterministic branch name based on the selected product area and triage bucket
- allowed implementation files and test files derived from the plan `suggested_files`
- red/green/verification command groups
- handoff checklist items for branch creation, red tests, minimal implementation, verification, PR, and merge

## CLI

Add:

```bash
albu-mcp activation product-fix-execution-guard --host Codex --format json
albu-mcp activation product-fix-execution-guard --host Codex --output-dir docs/product-fix-execution-guard --format markdown
```

Arguments mirror the previous product-fix planning command: `--host`, `--host-records`, `--beta-records`, `--release-tag`, `--output-dir`, and `--format`.

## Artifacts

When `--output-dir` is provided, write:

- `product-fix-execution-guard-index.md/json`
- `branch-scaffold.md/json`
- `execution-checklist.md/json`

Artifacts are safe to regenerate and must not modify host or beta evidence files.

## Testing

Use CLI-level tests with temporary host and beta records:

- blocked records produce a blocked guard and do not mutate inputs
- ready records produce branch scaffold details and command groups
- artifact output writes exactly the expected files and keeps records unchanged
- usage docs list the new command

Run focused tests first, then ruff, ty, release readiness, build, and full pytest before merging.
