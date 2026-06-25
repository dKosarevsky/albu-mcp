# Host Proof Sprint

This sprint proves the First 10 Minutes workflow in real MCP hosts without marking evidence as passed before a reviewer
actually runs the host UI.

Current machine-verifiable status is tracked in [docs/HOST_PROOF_STATUS.md](HOST_PROOF_STATUS.md). It does not replace
manual host UI evidence.

The generated host-by-host execution checklist is [docs/HOST_PROOF_SPRINT_CHECKLIST.md](HOST_PROOF_SPRINT_CHECKLIST.md).
The current manual evidence sprint board is [docs/HOST_EVIDENCE_SPRINT_BOARD.md](HOST_EVIDENCE_SPRINT_BOARD.md).

## Goal

Record dated `first_10_minutes_replay` evidence for at least:

1. Codex
2. Claude Code

Then extend the same replay to Cursor and Claude Desktop.

The replay validates the product path from [docs/FIRST_10_MINUTES.md](FIRST_10_MINUTES.md), not only low-level server
startup.

## Reviewer packet

Generate a host-specific packet:

```bash
uv run python scripts/export_manual_host_acceptance_packet.py --host Codex --output /tmp/albu-host-codex.md
uv run python scripts/export_manual_host_acceptance_packet.py --host "Claude Code" --output /tmp/albu-host-claude-code.md
uv run python scripts/export_host_proof_sprint_checklist.py --output docs/HOST_PROOF_SPRINT_CHECKLIST.md
uv run python scripts/export_host_evidence_sprint_board.py --output docs/HOST_EVIDENCE_SPRINT_BOARD.md
```

Each packet includes host config, bounded roots, the sample image path, the full acceptance prompt, and recording
commands.

For the shorter product path, run [examples/first_10_minutes_prompt.md](../examples/first_10_minutes_prompt.md) in the
host. It must use the same `--allowed-root` and `--artifact-root` values as the packet.

## Required replay sequence

The host must complete this sequence:

1. Read `albumentationsx://examples/client-smoke`.
2. Call `run_host_smoke_check`.
3. Call `plan_dataset_onboarding`.
4. Call `validate_preview_request`.
5. Call `render_preview_batch` only after validation returns `valid=true`.
6. Give concrete feedback and call `adjust_pipeline`.
7. Render a candidate preview.
8. Call `compare_preview_runs`.
9. Call `export_pipeline`.

The reviewer evidence must mention smoke check, validation, baseline render, candidate render, comparison, export, and at
least one artifact path.

## Record replay evidence

Record a passed replay only after the host UI actually completes the sequence:

```bash
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed \
  --date 2026-06-23 \
  --evidence "Codex completed smoke check, preview validation, baseline and candidate render, comparison, and export." \
  --artifact docs/assets/demo/demo_report.md
```

Use `blocked` when the host cannot complete the flow:

```bash
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status blocked \
  --date 2026-06-23 \
  --evidence "Codex could not list MCP tools after config reload." \
  --artifact docs/assets/demo/demo_report.md
```

## Verify evidence

Check one host:

```bash
uv run python scripts/check_first_10_minutes_replay.py --host Codex
```

Check every supported host:

```bash
uv run python scripts/check_first_10_minutes_replay.py
```

Regenerate the review artifact after recording evidence:

```bash
uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md
uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md
uv run python scripts/export_host_proof_sprint_checklist.py --output docs/HOST_PROOF_SPRINT_CHECKLIST.md
uv run python scripts/export_host_evidence_sprint_board.py --output docs/HOST_EVIDENCE_SPRINT_BOARD.md
uv run python scripts/check_host_acceptance_report.py
```

The committed [docs/HOST_ACCEPTANCE_EVIDENCE.md](HOST_ACCEPTANCE_EVIDENCE.md) should stay `pending` until real host UI
evidence is recorded.

## Readiness guard

This sprint runbook is checked by:

```bash
uv run python scripts/check_host_proof_sprint.py
```

The guard confirms that the runbook, replay schema, README link, and host acceptance checklist stay wired together.
