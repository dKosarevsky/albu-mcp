# Post-import review

Phase id: `post_import_review`

Status: `blocked_until_host_closed`

Writes records: `false`

## Goal

Review proof status, trust transition, and RC blockers after real evidence records change.

## Next Commands

- `albu-mcp evidence proof-status --format json`
- `albu-mcp evidence transition-pack --before-host-records docs/HOST_MANUAL_RUNS.json --after-host-records docs/HOST_MANUAL_RUNS.json --beta-records docs/BETA_VALIDATION_RECORDS.json --output-dir docs/operator-packets --format markdown`
- `albu-mcp evidence rc-unblock-preview --format json`
