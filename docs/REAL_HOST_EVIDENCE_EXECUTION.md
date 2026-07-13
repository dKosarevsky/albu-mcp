# Real Host Evidence Execution Pack

Package: `albumentationsx-mcp==1.18.0`
Decision: `hold_v1`
Ready for v1: `false`

## Non-Fabrication Policy

Record passed only after a real MCP host UI completes the flow.
Keep hosts pending or blocked until the reviewer has a dated real UI observation.

## Execution Queue

| Order | Host | Priority | Next Action | Packet |
| --- | --- | --- | --- | --- |
| 1 | Claude Code | `p0` | `triage_blocker` | `uv run python scripts/export_manual_host_acceptance_packet.py --host 'Claude Code' --output /tmp/albu-host-claude-code.md` |
| 2 | Cursor | `p1` | `run_first_10_minutes_replay` | `uv run python scripts/export_manual_host_acceptance_packet.py --host Cursor --output /tmp/albu-host-cursor.md` |
| 3 | Claude Desktop | `p1` | `run_first_10_minutes_replay` | `uv run python scripts/export_manual_host_acceptance_packet.py --host 'Claude Desktop' --output /tmp/albu-host-claude-desktop.md` |

## Reviewer Worksheet

### Claude Code

- Packet: `uv run python scripts/export_manual_host_acceptance_packet.py --host 'Claude Code' --output /tmp/albu-host-claude-code.md`
- Next action: `triage_blocker`
- Required observations:
  - Host shows AlbumentationsX MCP tools and resources.
  - Host completes run_host_smoke_check.
  - Host validates the preview request before rendering.
  - Host renders baseline and candidate previews under artifact root.
  - Host compares preview runs and exports a pipeline or report.
- Status decision: `passed`, `blocked`, or `pending`.
- Evidence note: one redacted sentence naming completed gates and the first blocker if any.

### Cursor

- Packet: `uv run python scripts/export_manual_host_acceptance_packet.py --host Cursor --output /tmp/albu-host-cursor.md`
- Next action: `run_first_10_minutes_replay`
- Required observations:
  - Host shows AlbumentationsX MCP tools and resources.
  - Host completes run_host_smoke_check.
  - Host validates the preview request before rendering.
  - Host renders baseline and candidate previews under artifact root.
  - Host compares preview runs and exports a pipeline or report.
- Status decision: `passed`, `blocked`, or `pending`.
- Evidence note: one redacted sentence naming completed gates and the first blocker if any.

### Claude Desktop

- Packet: `uv run python scripts/export_manual_host_acceptance_packet.py --host 'Claude Desktop' --output /tmp/albu-host-claude-desktop.md`
- Next action: `run_first_10_minutes_replay`
- Required observations:
  - Host shows AlbumentationsX MCP tools and resources.
  - Host completes run_host_smoke_check.
  - Host validates the preview request before rendering.
  - Host renders baseline and candidate previews under artifact root.
  - Host compares preview runs and exports a pipeline or report.
- Status decision: `passed`, `blocked`, or `pending`.
- Evidence note: one redacted sentence naming completed gates and the first blocker if any.

## After Each Host Run

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md`
- `uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md`
- `uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md`
- `uv run python scripts/export_host_evidence_sprint_board.py --output docs/HOST_EVIDENCE_SPRINT_BOARD.md`
- `uv run python scripts/check_release_readiness.py`
