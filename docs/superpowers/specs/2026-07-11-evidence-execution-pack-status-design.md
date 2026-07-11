# Evidence Execution Pack Status Design

## Goal

Add one report-only command that tells an operator whether an evidence execution pack is structurally blocked, still
needs real host or beta input, or is ready for import review. The report must expose the next concrete actions without
writing records or treating generated templates as evidence.

## Considered Approaches

1. Add status logic to `evidence_execution_pack.py`. This keeps the feature nearby but further expands a module that
   already owns generation, audit, progress, rendering, and low-level validation helpers.
2. Add a focused status orchestration module. This composes the existing audit, progress, and no-write import wizard
   contracts while keeping status decisions and rendering isolated. This is the selected approach.
3. Compose existing CLI commands through subprocesses. This avoids Python imports but weakens typing, error handling,
   testability, and portability.

## Architecture

Create `evidence_execution_pack_status.py` as an application-level composition module. It receives only paths, calls
the existing audit and progress builders, and calls the import wizard in no-write mode when the pack structure is
valid. `cli.py` remains an adapter for arguments, output selection, and optional report-file writing.

The status module must not parse manifests or beta drafts itself. Validation ownership remains in the existing
evidence, beta, execution-pack, and import-wizard modules.

## Command

```bash
albu-mcp evidence execution-pack-status \
  --input-dir evidence-session \
  --format markdown
```

Optional `--host-records`, `--beta-records`, and `--output` arguments match the adjacent audit and progress commands.
JSON is the default format; Markdown is the operator-facing view.

## Output Contract

The top-level report contains:

- `status`: `blocked`, `needs_real_session_input`, or `ready_for_import_review`
- `writes_records`: always `false`
- `audit_status`, `progress_status`, and `import_wizard_status`
- total/completed/pending host/pending beta item counts
- `import_ready_command_available`: true only when the no-write wizard reports `ready_to_import`
- `blocking_reasons`, `next_action`, and at most three `next_commands`
- nested audit, progress, and optional import-wizard reports for machine consumers
- an explicit non-fabrication policy

`import_ready_command_available=true` means the validated inputs are eligible for a reviewer-approved
`import-wizard --import-ready` run. It does not perform that run and does not imply automatic approval.

## Decision Rules

- A blocked audit produces `blocked`; the import wizard is not run.
- A valid pack with pending host or beta fields produces `needs_real_session_input`.
- A fully completed pack produces `ready_for_import_review` only when the no-write import wizard independently reports
  `ready_to_import`.
- If progress says ready but the wizard rejects the inputs, the final status is `blocked` and wizard blockers are
  surfaced with an `import_wizard:` prefix.

## Error And Safety Boundaries

Missing or invalid pack files are returned as report blockers, following existing audit behavior. The command does not
mutate the execution pack, host records, or beta records. Only the existing explicit `import-wizard --import-ready`
command may write records after reviewer approval.

## Testing

CLI tests cover a generated template pack, a structurally incomplete pack, and a fully filled pack. They assert status
transitions, bounded next actions, no-write behavior, and JSON/Markdown rendering. Documentation contract tests cover
the public usage guide and packaged agent skill. The full pytest, ruff, ty, template guard, evidence preflight, and
package build gates run before merge.
