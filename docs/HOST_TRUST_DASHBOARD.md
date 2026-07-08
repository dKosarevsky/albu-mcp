# Host Trust Dashboard

Records path: `docs/HOST_MANUAL_RUNS.json`

Dashboard status: `blocked`

Execution policy: `report_only`. This report does not write evidence records.

Next host: `Codex`

## Host Lanes

| Host | Priority | Overall | Manual Host UI | First 10 Minutes | Next Action | Next Command |
| --- | --- | --- | --- | --- | --- | --- |
| Codex | `p0` | `blocked` | `blocked` | `blocked` | Triage blocker | `albu-mcp evidence collect --host Codex --date YYYY-MM-DD --reviewer '<reviewer>' --format markdown` |
| Claude Code | `p0` | `blocked` | `blocked` | `blocked` | Triage blocker | `albu-mcp evidence collect --host 'Claude Code' --date YYYY-MM-DD --reviewer '<reviewer>' --format markdown` |
| Claude Desktop | `p1` | `pending` | `missing` | `missing` | Collect real host evidence | `albu-mcp evidence collect --host 'Claude Desktop' --date YYYY-MM-DD --reviewer '<reviewer>' --format markdown` |
| Cursor | `p1` | `pending` | `missing` | `missing` | Collect real host evidence | `albu-mcp evidence collect --host Cursor --date YYYY-MM-DD --reviewer '<reviewer>' --format markdown` |

## Regenerate

```bash
albu-mcp host next-action --include-session --format markdown --output docs/HOST_TRUST_DASHBOARD.md
```

## Guided Session

`host`: `Codex`

`next_gate`: `first_10_minutes_replay`

`manifest_path`: `docs/operator-packets/codex-evidence-session-manifest.json`

`writes_records`: `false`

### Commands

- `collect`: `albu-mcp evidence collect --host Codex --date YYYY-MM-DD --reviewer '<reviewer>' --format markdown`
- `session_manifest`: `albu-mcp evidence session-manifest --host Codex --date YYYY-MM-DD --reviewer '<reviewer>' --output-dir docs/operator-packets --format json`
- `validate_manifest`: `albu-mcp evidence validate-manifest --input docs/operator-packets/codex-evidence-session-manifest.json --format json`
- `import_artifacts`: `albu-mcp evidence import-artifacts --host Codex --status passed --date YYYY-MM-DD --evidence '<redacted reviewer-observed evidence>' --artifact docs/assets/demo/demo_report.md --confirm-real-host-observed`
- `privacy_doctor`: `albu-mcp evidence privacy-doctor --format json`
- `artifact_doctor`: `albu-mcp evidence artifact-doctor --format json`
- `regenerate_dashboard`: `albu-mcp host next-action --include-session --format markdown --output docs/HOST_TRUST_DASHBOARD.md`

### Stop Conditions

- Do not run import_artifacts until a reviewer observes the real MCP host UI session.
- Do not record passed evidence without --confirm-real-host-observed.
- Do not commit private dataset paths or file:// artifact references.
- Do not treat generated smoke output as manual host evidence.

## Operator Rules

- Record `passed` only after reviewer-observed real MCP host UI evidence.
- Keep private dataset paths out of committed evidence records.
- Use the next command to collect evidence; import only after manifest validation.
