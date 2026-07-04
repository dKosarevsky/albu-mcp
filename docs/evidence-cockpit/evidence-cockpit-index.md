# Real Evidence Execution Cockpit

Release tag: `v1.15.0-rc.1`

Host: `Codex`

Cockpit status: `blocked`

Writes records: `false`

Next action: `run_setup_probe`

## Phases

- `setup_probe`: `ready_to_run`; writes_records=`false`
- `session_capture`: `blocked_until_setup_probe`; writes_records=`false`
- `manifest_import`: `blocked_until_reviewer_observed_real_host`; writes_records=`false`
- `post_import_review`: `blocked_until_host_closed`; writes_records=`false`

## Non-Fabrication Policy

The cockpit only sequences commands and writes optional generated handoffs. It does not record P0 evidence; import commands must be run only after reviewer-observed real MCP host UI evidence exists.
