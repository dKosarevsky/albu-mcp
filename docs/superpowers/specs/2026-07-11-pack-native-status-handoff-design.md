# Pack-Native Status Handoff Design

## Goal

Make every generated evidence execution pack self-guiding. An operator opening only the pack must discover the
no-write `execution-pack-status` command, know where its report is written, and see a safe sequence that keeps
reviewer-approved record import separate from validation.

## Scope

This iteration changes generated Markdown artifacts and their documentation. It does not add another CLI command,
change evidence validation rules, import records, fabricate evidence, or alter the three status states introduced by
`execution-pack-status`.

## Considered Approaches

1. Document the command only in repository docs. This is already available but fails when an operator receives only a
   generated pack.
2. Embed one canonical command in generated pack artifacts. This is selected because the workflow becomes locally
   discoverable without adding a new runtime abstraction.
3. Generate `status.md` eagerly with the pack. This is rejected because the initial report is immediately stale after
   manual edits and could be mistaken for current evidence state.

## Architecture

Keep ownership in `evidence_execution_pack.py`. Add one private command builder that accepts the existing
`EvidenceExecutionPackRequest` and returns a shell-safe command using the module's path quoting helper. Both generated
`README.md` and `post-session-commands.md` consume that builder, so flags and paths cannot drift.

The status command writes only `<output-dir>/status.md` and passes the pack's configured host and beta record paths:

```bash
albu-mcp evidence execution-pack-status \
  --input-dir <output-dir> \
  --host-records <host-records> \
  --beta-records <beta-records> \
  --format markdown \
  --output <output-dir>/status.md
```

## Generated README

Add an `Operator Status` section that instructs the operator to run the command after generating the pack and after
every evidence edit. It states that `status.md` is a report, not evidence, and that records remain unchanged.

Do not list `status.md` among initial artifacts because it does not exist until the operator runs the command.

## Post-Session Sequence

Organize `post-session-commands.md` in this order:

1. `Pack Status`: run the copy-ready no-write status command.
2. Per-input host and beta validation commands.
3. Existing no-write preflight.
4. `Import Wizard (No Write)`: generate `import-wizard.md` without importing.
5. `Reviewed Import (Writes Records)`: show `--import-ready` separately.

The reviewed import section must say that both `status.md` and `import-wizard.md` must report readiness and that a
reviewer must explicitly approve the import. Static artifacts cannot hide the import command dynamically, so the
safety boundary remains validator enforcement plus explicit operator approval.

## Path Safety

All paths use `shlex.quote` through the existing `_quote_path` helper. Tests must cover output and record paths that
contain spaces and must execute the rendered command after parsing it with `shlex.split`.

## Testing

Add an integration-style CLI test that:

- generates a pack under paths containing spaces;
- asserts the identical command appears in both generated artifacts;
- confirms `status.md` is absent initially;
- executes the rendered command;
- confirms `status.md` reports `needs_real_session_input` and `writes_records: false`;
- proves host and beta record files are byte-for-byte unchanged.

Documentation and packaged-skill contract tests must require the report-writing command. The full pytest, ruff, ty,
template guard, preflight, release readiness, and package build gates run before merge.
