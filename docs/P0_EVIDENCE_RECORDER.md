# P0 Evidence Recorder

Target hosts: `Codex, Claude Code`

## Recording Policy

Record only redacted, reviewer-observed host UI evidence.

## Privacy Notes

- Do not record private screenshots, prompts, tokens, or full host logs.
- Record the first failing gate when status is blocked.
- Keep pending when a host was not run in the real UI.

## Required Fields

- `host`
- `gate`
- `status`
- `date`
- `evidence`
- `artifact`

## Record Commands

### Codex

#### first_10_minutes_replay

```bash
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex first_10_minutes_replay passed in the real host UI with redacted reviewer-observed evidence.' --artifact docs/assets/demo/demo_report.md
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status blocked --date YYYY-MM-DD --evidence 'Codex first_10_minutes_replay blocked at <first failing gate>; redacted symptom: <symptom>.' --artifact docs/assets/demo/demo_report.md
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status pending --date YYYY-MM-DD --evidence 'Codex first_10_minutes_replay was not run in the real host UI.' --artifact docs/assets/demo/demo_report.md
```

#### manual_host_ui

```bash
uv run python scripts/record_host_manual_run.py --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex manual_host_ui passed in the real host UI with redacted reviewer-observed evidence.'
uv run python scripts/record_host_manual_run.py --host Codex --status blocked --date YYYY-MM-DD --evidence 'Codex manual_host_ui blocked at <first failing gate>; redacted symptom: <symptom>.'
uv run python scripts/record_host_manual_run.py --host Codex --status pending --date YYYY-MM-DD --evidence 'Codex manual_host_ui was not run in the real host UI.'
```

### Claude Code

#### first_10_minutes_replay

```bash
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code first_10_minutes_replay passed in the real host UI with redacted reviewer-observed evidence.' --artifact docs/assets/demo/demo_report.md
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status blocked --date YYYY-MM-DD --evidence 'Claude Code first_10_minutes_replay blocked at <first failing gate>; redacted symptom: <symptom>.' --artifact docs/assets/demo/demo_report.md
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status pending --date YYYY-MM-DD --evidence 'Claude Code first_10_minutes_replay was not run in the real host UI.' --artifact docs/assets/demo/demo_report.md
```

#### manual_host_ui

```bash
uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code manual_host_ui passed in the real host UI with redacted reviewer-observed evidence.'
uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status blocked --date YYYY-MM-DD --evidence 'Claude Code manual_host_ui blocked at <first failing gate>; redacted symptom: <symptom>.'
uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status pending --date YYYY-MM-DD --evidence 'Claude Code manual_host_ui was not run in the real host UI.'
```

## After Recording

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md`
- `uv run python scripts/check_release_readiness.py`
