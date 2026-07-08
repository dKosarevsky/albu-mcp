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
albu-mcp host next-action --format markdown --output docs/HOST_TRUST_DASHBOARD.md
```

## Operator Rules

- Record `passed` only after reviewer-observed real MCP host UI evidence.
- Keep private dataset paths out of committed evidence records.
- Use the next command to collect evidence; import only after manifest validation.
