# Host Proof Status

Current release: `v1.15.0`

This status separates machine-verifiable MCP proof from real host UI evidence. Do not mark manual host runs as passed
until a reviewer completes the flow in the actual host UI.

## Machine Proof

- Release workflow: `28049320843`
- Manual MCP Registry verification workflow: `28049831952`
- PyPI package: `albumentationsx-mcp==1.15.0`
- MCP Registry: `io.github.dKosarevsky/albu-mcp` active/latest for `1.15.0`
- Host proof packet generated for Codex and Claude Code with
  `scripts/export_manual_host_acceptance_packet.py --host Codex --host "Claude Code"`.

Verified commands:

```bash
uv run python scripts/check_release_readiness.py --tag v1.15.0
uv run python scripts/check_mcp_registry_status.py --retries 6 --retry-delay 10 --timeout 30
uv run python scripts/check_published_package_smoke.py --version 1.15.0
uv run python scripts/export_manual_host_acceptance_packet.py --host Codex --host "Claude Code"
uv run python scripts/run_golden_evals.py --work-dir /private/tmp/albu-mcp-host-proof-golden
```

Golden stdio replay completed:

```text
client_smoke_resource_flow: ok
diagnostics_resource_flow: ok
first_preview_resource_prompt_flow: ok
distortion_review_resource_flow: ok
dataset_onboarding_flow: ok
segmentation_onboarding_flow: ok
classification_recommend_validate_explain_export: ok
preview_lifecycle: ok
preview_batch_compare: ok
preview_quality_tuning_summary: ok
real_sample_preview_smoke: ok
preview_request_troubleshooting: ok
interactive_tuning_session_flow: ok
```

## Manual Host Evidence

- Manual Host UI: pending
- First 10 Minutes Replay: pending

Current replay gate:

```bash
uv run python scripts/check_first_10_minutes_replay.py --host Codex --host "Claude Code"
```

Result: pending for both Codex and Claude Code because no real host UI replay has been recorded in
`docs/HOST_MANUAL_RUNS.json`.
