# Evidence Preflight

Preflight status: `blocked`

Writes records: `false`

Template guard: `passed`

Import wizard: `blocked`

Proof status: `blocked`

RC preview: `blocked`

## Blocking Reasons

- `import_wizard:host_manifest_not_ready`
- `import_wizard:beta_draft_not_ready`

## Evidence Blockers

- `proof_status:Codex:manual_host_ui`
- `proof_status:Codex:first_10_minutes_replay`
- `proof_status:Claude Code:manual_host_ui`
- `proof_status:Claude Code:first_10_minutes_replay`
- `rc_unblock:p0_host_evidence_missing_or_blocked`
- `rc_unblock:beta_validation_incomplete`

## Next Commands

- `Fill reviewer-observed host manifests before import.`
- `Fill privacy-safe beta response drafts before import.`
- `albu-mcp evidence proof-status --format json`
- `albu-mcp beta loop-pack --output-dir docs/beta-loop --format markdown`
- `albu-mcp rc go-check --format markdown`

## Non-Fabrication Policy

Evidence preflight is report-only. It reads template, import, and release blocker state without writing records, inferring outcomes, creating tags, or treating generated templates as evidence.
