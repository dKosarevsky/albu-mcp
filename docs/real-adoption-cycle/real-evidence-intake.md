# Real evidence intake

Lane id: `real_evidence_intake`

Status: `blocked_until_real_host_evidence`

Writes records: `false`

## Summary

- none

## Blocked Reasons

- `p0_host_evidence_missing_or_blocked`

## Next Commands

- `albu-mcp activation evidence-cockpit --host Codex --output-dir docs/evidence-cockpit --format markdown`
- `albu-mcp evidence proof-runner --input docs/operator-packets/codex-evidence-session-manifest.json --format json`
- `albu-mcp evidence import-manifest --input docs/operator-packets/codex-evidence-session-manifest.json --format json`
