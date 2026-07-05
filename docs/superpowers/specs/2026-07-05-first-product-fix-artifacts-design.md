# First Product Fix Artifacts Design

## Goal

Make `activation first-product-fix` usable as an operator handoff by adding an artifact-only pack for selector output,
selected-fix details, and implementation checklist.

## Scope

The command gains `--output-dir` support:

```bash
albu-mcp activation first-product-fix --host Codex --output-dir docs/first-product-fix --format markdown
```

The pack reads the same inputs as the selector:

- `docs/HOST_MANUAL_RUNS.json`
- `docs/BETA_VALIDATION_RECORDS.json`
- real adoption cycle status
- beta validation decisions

It writes only generated operator artifacts under the requested output directory. It never imports host evidence, writes
beta validation records, changes product backlog files, or creates implementation branches.

## Artifacts

For Markdown output, write:

- `first-product-fix-index.md`: selector status, implementation gate, next commands
- `selected-fix.md`: selected fix details when ready, or blocked reasons when not ready
- `implementation-checklist.md`: TDD, evidence safety, and verification checklist

For JSON output, write the same payloads as `.json` files.

## Behavior

When external gates are blocked, the pack is still useful: it writes blocked artifacts with exact reasons and commands to
collect real host or beta data.

When gates are green, the pack writes the selected product area, candidate scope, success signal, suggested files, and
test strategy from the selector implementation packet.

## Testing

Add CLI tests that:

- run blocked records through `--output-dir` and verify three Markdown artifacts are written
- run ready records through `--output-dir --format json` and verify selected-fix plus implementation checklist payloads
- assert no host or beta record files are modified

