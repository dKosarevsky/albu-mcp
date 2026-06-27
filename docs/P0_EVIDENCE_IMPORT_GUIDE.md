# P0 Evidence Import Guide

Guide status: `verify-only`
Records path: `docs/HOST_MANUAL_RUNS.json`
Target hosts: `Codex, Claude Code`
Required gates: `first_10_minutes_replay, manual_host_ui`

## Policy

This helper is verify-only: it validates proposed manual evidence and returns recording commands. It does not write `docs/HOST_MANUAL_RUNS.json`.

## Verify Candidate Evidence

```bash
uv run python scripts/verify_host_evidence_import.py --input /path/to/host-evidence-candidate.json
```

The verifier accepts either a flat `records` list with `kind` or the canonical `manual_host_ui` / `first_10_minutes_replay` shape.

## Sample Input

```json
{
  "records": [
    {
      "kind": "manual_host_ui",
      "host": "Codex",
      "status": "passed",
      "date": "2026-06-28",
      "evidence": "Codex host UI listed the MCP tools and run_host_smoke_check returned preview_ready true."
    },
    {
      "kind": "first_10_minutes_replay",
      "host": "Codex",
      "status": "passed",
      "date": "2026-06-28",
      "evidence": "Codex completed smoke, preview validation, render_preview_batch, comparison, and export.",
      "artifacts": [
        "docs/assets/demo/demo_report.md"
      ]
    }
  ]
}
```

## Recording

The verifier returns copyable scripts/record_host_manual_run.py commands.

## After Recording

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md`
- `uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md`
- `uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md`
- `uv run python scripts/check_release_readiness.py`
