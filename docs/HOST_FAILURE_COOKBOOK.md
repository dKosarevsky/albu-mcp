# Host Failure Cookbook

## Privacy Policy

Keep private datasets, prompts, screenshots, local home paths, tokens, and full host logs out of committed evidence. Record only redacted symptoms and the first failing gate.

## Failure Cases

### tools_not_visible

- Symptom: The host starts but does not show AlbumentationsX MCP tools.
- First check: Ask the host to read `albumentationsx://examples/client-smoke`.
- Fix: Restart the host, verify MCP config shape, then run `run_host_smoke_check` after tools appear.
- Record status: `blocked`
- Evidence note: Host could not list AlbumentationsX MCP tools after config reload.

### stale_tool_cache

- Symptom: The host shows an older tool list after package or config changes.
- First check: Restart the host and clear client-side MCP server discovery cache.
- Fix: Confirm the host sees the current `albumentationsx-mcp` version and rerun client smoke.
- Record status: `blocked`
- Evidence note: Host kept stale MCP tool discovery after package upgrade.

### path_policy_rejected

- Symptom: Preview validation rejects local images or directories.
- First check: Run `diagnose_environment` and inspect `fix_allowed_root` remediation.
- Fix: Restart the server with an existing absolute `--allowed-root` that contains the sample image.
- Record status: `blocked`
- Evidence note: Host path policy rejected the configured allowed root or sample image.

### artifact_root_unwritable

- Symptom: Preview rendering starts but artifacts, manifests, or contact sheets are missing.
- First check: Check artifact root permissions outside the host.
- Fix: Restart with a writable absolute `--artifact-root` and rerun `render_preview_batch`.
- Record status: `blocked`
- Evidence note: Host could not write preview artifacts under the configured artifact root.

### uvx_startup_failed

- Symptom: The host cannot start the MCP server process.
- First check: Run the exact `uvx` command in a terminal.
- Fix: Fix terminal startup errors first, then paste the same command back into host config.
- Record status: `blocked`
- Evidence note: Host could not start the `uvx` MCP server command.

## Record Blocked Evidence

- `uv run python scripts/export_manual_host_acceptance_packet.py --host '<host>' --output /tmp/albu-host-<host>.md`
- `uv run python scripts/record_host_manual_run.py --host '<host>' --status blocked --date YYYY-MM-DD --evidence '<redacted blocker note>'`
- `uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md`
- `uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md`
- `uv run python scripts/export_host_evidence_sprint_board.py --output docs/HOST_EVIDENCE_SPRINT_BOARD.md`
