# Host Proof Status

Current release target: `v1.19.0`

This status separates machine-verifiable MCP proof from real host UI evidence. Do not mark manual host runs as passed
until a reviewer completes the flow in the actual host UI.

## Machine Proof

- Release workflow: tag-triggered through `.github/workflows/release.yml`
- MCP Registry verification: automated after the published-package smoke check
- PyPI package target: `albumentationsx-mcp==1.19.0`
- MCP Registry target: `io.github.dKosarevsky/albu-mcp` version `1.19.0`
- GitHub Release target: Python artifacts plus `albumentationsx-mcp-1.19.0.mcpb`, the byte-identical
  `albumentationsx-mcp.mcpb` alias, and `SHA256SUMS`
- Host proof packet generated for Codex and Claude Code with
  `scripts/export_manual_host_acceptance_packet.py --host Codex --host "Claude Code"`.

Verified commands:

```bash
uv run python scripts/check_release_readiness.py --tag v1.19.0
uv run python scripts/export_manual_host_acceptance_packet.py --host Codex --host "Claude Code"
uv run python scripts/run_golden_evals.py --work-dir /private/tmp/albu-mcp-host-proof-golden
```

After publication, verify PyPI and Registry propagation with:

```bash
uv run python scripts/check_published_package_smoke.py --version 1.19.0
uv run python scripts/check_mcp_registry_status.py --retries 6 --retry-delay 10 --timeout 30
```

Golden stdio replay completed:

```text
client_smoke_resource_flow: ok
diagnostics_resource_flow: ok
first_preview_resource_prompt_flow: ok
distortion_review_resource_flow: ok
dataset_onboarding_flow: ok
segmentation_onboarding_flow: ok
review_packet_flow: ok
dataset_quality_inspection_flow: ok
classification_recommend_validate_explain_export: ok
preview_lifecycle: ok
preview_batch_compare: ok
preview_quality_tuning_summary: ok
real_sample_preview_smoke: ok
preview_request_troubleshooting: ok
interactive_tuning_session_flow: ok
```

## MCP Apps Machine Proof

The `v1.19.0` interactive review surface passed the official `@modelcontextprotocol/ext-apps` `1.7.4`
basic-host replay on 2026-07-13. The generated-fixture run covered verified artifact reads, image and overlay review,
feedback persistence, accept decisions, fullscreen, desktop/mobile layout, and the non-MCP-Apps fallback contract.

The exact reference commit, bounded loopback harness, measured results, and evidence classification are in
[MCP_APPS_BASIC_HOST_PROOF.md](MCP_APPS_BASIC_HOST_PROOF.md). This is machine proof, not a new manual production-host,
beta, or adoption record.

## Manual Host Evidence

- Codex Manual Host UI: passed on 2026-07-11
- Codex First 10 Minutes Replay: passed on 2026-07-11
- Claude Desktop Manual Host UI: passed on 2026-07-13
- Claude Desktop First 10 Minutes Replay: pending
- Claude Code Manual Host UI: blocked
- Claude Code First 10 Minutes Replay: blocked

Current replay gate:

```bash
uv run python scripts/check_first_10_minutes_replay.py --host Codex --host "Claude Code"
```

Result: Codex is recorded; Claude Desktop manual UI is recorded while its full replay remains pending; Claude Code
remains blocked because the CLI was unavailable in the observed environment. Canonical evidence and sanitized receipts
are in `docs/HOST_MANUAL_RUNS.json` and `docs/host-evidence/`.
