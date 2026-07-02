# Host Setup Probe

Probe status: `manual_probe_required`
Live probe: `false`
Writes records: `false`
Allowed root: `/absolute/path/to/images`
Artifact root: `/absolute/path/to/albu-artifacts`

## Non-Evidence Policy

Setup probes only validate local readiness. They do not record P0 evidence or replace reviewer-observed real MCP host UI runs.

## Summary

- host_count: `4`
- check_count: `6`
- passed_check_count: `2`
- failed_check_count: `0`
- not_run_check_count: `4`

## Checks

| Check | Status | Detail | Remediation |
| --- | --- | --- | --- |
| `uvx` | `not_run` | Run `command -v uvx` in the host operator shell. | Install or expose `uvx` before relying on host setup. |
| `claude_cli` | `not_run` | Run `command -v claude` in the host operator shell. | Install or expose `claude` before relying on host setup. |
| `allowed_root` | `not_run` | Replace `/absolute/path/to/images` with a local absolute path before preview work. | Use the smallest useful local root and keep generated artifacts outside source datasets. |
| `artifact_root` | `not_run` | Replace `/absolute/path/to/albu-artifacts` with a local absolute path before preview work. | Use the smallest useful local root and keep generated artifacts outside source datasets. |
| `package_command` | `passed` | uvx --from albumentationsx-mcp albumentationsx-mcp | Use the published PyPI package command from docs/INSTALL.md. |
| `bounded_roots` | `passed` | Use --allowed-root and --artifact-root for preview work. | Keep local image reads and generated artifacts scoped to explicit directories. |

## Host Lanes

| Host | Setup Doc | Operator Command | Required Checks | Blocking Checks | Next Action |
| --- | --- | --- | --- | --- | --- |
| Codex | `examples/codex_preview_mcp_config.toml` | `uvx --from albumentationsx-mcp albumentationsx-mcp` | `uvx`, `allowed_root`, `artifact_root`, `package_command`, `bounded_roots` | `none` | `run_evidence_collect` |
| Claude Code | `examples/claude_code_preview_command.md` | `claude mcp add albumentationsx -- uvx --from albumentationsx-mcp albumentationsx-mcp` | `uvx`, `claude_cli`, `allowed_root`, `artifact_root`, `package_command`, `bounded_roots` | `none` | `run_evidence_collect` |
| Cursor | `examples/cursor_preview_mcp_config.json` | `uvx --from albumentationsx-mcp albumentationsx-mcp` | `uvx`, `allowed_root`, `artifact_root`, `package_command`, `bounded_roots` | `none` | `run_evidence_collect` |
| Claude Desktop | `examples/claude_desktop_preview_config.json` | `uvx --from albumentationsx-mcp albumentationsx-mcp` | `uvx`, `allowed_root`, `artifact_root`, `package_command`, `bounded_roots` | `none` | `run_evidence_collect` |

## Post-Probe Commands

- `uv run python scripts/check_host_setup_probe.py --live --format json`
- `albu-mcp host setup-probe --live --format json`
- `uv run python scripts/check_p0_host_run_preflight.py`
- `albu-mcp evidence collect --host Codex --format json`
- `uv run python scripts/check_release_readiness.py`

## Source Docs

- `docs/INSTALL.md`
- `docs/HOST_MATRIX.md`
- `docs/HOST_FAILURE_COOKBOOK.md`
- `docs/HOST_EVIDENCE_RUNNER.md`
