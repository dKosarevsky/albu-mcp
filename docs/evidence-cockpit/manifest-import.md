# Manifest import

Phase id: `manifest_import`

Status: `blocked_until_reviewer_observed_real_host`

Writes records: `false`

## Goal

Validate and import a filled manifest only after real host evidence is observed by a reviewer.

## Next Commands

- `albu-mcp evidence proof-runner`
- `albu-mcp evidence validate-manifest`
- `albu-mcp evidence import-manifest`
- `albu-mcp evidence close-host --host Codex --format json`
