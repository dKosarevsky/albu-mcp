# Host UX Hardening Loop

## Source Reports

- `docs/V1_LAUNCH_REPORT.md`
- `docs/HOST_FAILURE_COOKBOOK.md`
- `docs/HOST_MANUAL_RUNS.json`

## Hardening Queue

| Host | Priority | Gate | Evidence Status | Next Action |
| --- | --- | --- | --- | --- |
| Codex | `p0` | `first_10_minutes_replay` | `blocked` | `triage_blocker` |
| Codex | `p0` | `manual_host_ui` | `blocked` | `triage_blocker` |
| Claude Code | `p0` | `first_10_minutes_replay` | `blocked` | `triage_blocker` |
| Claude Code | `p0` | `manual_host_ui` | `blocked` | `triage_blocker` |
| Cursor | `p1` | `first_10_minutes_replay` | `missing` | `run_first_10_minutes_replay` |
| Cursor | `p1` | `manual_host_ui` | `missing` | `run_manual_host_ui` |
| Claude Desktop | `p1` | `first_10_minutes_replay` | `missing` | `run_first_10_minutes_replay` |
| Claude Desktop | `p1` | `manual_host_ui` | `missing` | `run_manual_host_ui` |

## Loop Steps

1. Record blocked evidence with the first failing host gate.
2. Classify the failure with the host failure cookbook.
3. Patch host UX docs, config snippets, diagnostics, or product behavior.
4. Add or update a regression test for the failure class.
5. Regenerate launch, decision, and execution reports.

## Triage Entrypoints

### Codex / first_10_minutes_replay

- `docs/HOST_FAILURE_COOKBOOK.md`
- `albumentationsx://diagnostics/guide`
- `run_host_smoke_check`

### Codex / manual_host_ui

- `docs/HOST_FAILURE_COOKBOOK.md`
- `albumentationsx://diagnostics/guide`
- `run_host_smoke_check`

### Claude Code / first_10_minutes_replay

- `docs/HOST_FAILURE_COOKBOOK.md`
- `albumentationsx://diagnostics/guide`
- `run_host_smoke_check`

### Claude Code / manual_host_ui

- `docs/HOST_FAILURE_COOKBOOK.md`
- `albumentationsx://diagnostics/guide`
- `run_host_smoke_check`

### Cursor / first_10_minutes_replay

- `docs/HOST_FAILURE_COOKBOOK.md`
- `albumentationsx://diagnostics/guide`
- `run_host_smoke_check`

### Cursor / manual_host_ui

- `docs/HOST_FAILURE_COOKBOOK.md`
- `albumentationsx://diagnostics/guide`
- `run_host_smoke_check`

### Claude Desktop / first_10_minutes_replay

- `docs/HOST_FAILURE_COOKBOOK.md`
- `albumentationsx://diagnostics/guide`
- `run_host_smoke_check`

### Claude Desktop / manual_host_ui

- `docs/HOST_FAILURE_COOKBOOK.md`
- `albumentationsx://diagnostics/guide`
- `run_host_smoke_check`

## Regression Targets

- `tests/test_host_failure_cookbook.py`
- `tests/test_host_ux_packets.py`
- `tests/test_manual_host_acceptance_packet.py`
- `tests/test_v1_launch_report.py`

## Regeneration Commands

- `uv run python scripts/export_host_failure_cookbook.py --output docs/HOST_FAILURE_COOKBOOK.md`
- `uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md`
- `uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md`
- `uv run python scripts/export_real_host_evidence_execution_pack.py --output docs/REAL_HOST_EVIDENCE_EXECUTION.md`
- `uv run python scripts/export_host_ux_hardening_loop.py --output docs/HOST_UX_HARDENING_LOOP.md`
