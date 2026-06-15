# v1.2 Diagnostics Design

AlbumentationsX MCP needs a first-class diagnostics surface so MCP hosts can answer installation and preview setup
questions without asking users to inspect logs. The feature adds a read-mostly `diagnose_environment` MCP tool and a
read-only `albumentationsx://diagnostics/guide` resource.

## Scope

The diagnostics flow checks server-local configuration and public MCP discovery. It reports:

- package import and version for `albumentationsx`;
- configured `allowed_roots`, `artifact_root`, and `max_preview_runs`;
- artifact root existence, directory type, writeability, and bounded probe cleanup;
- whether configured allowed roots currently exist;
- required public tools, workflow resources, and prompts advertised by `albumentationsx://capabilities`;
- agent-facing next actions for common setup failures.

It does not inspect user datasets, render previews, infer host-specific config files, or perform network checks. The only
side effect is creating and deleting one small probe file under `artifact_root` when `include_write_probe=true`.

## Architecture

Keep `server.py` as a thin adapter. Add a focused `diagnostics.py` module that owns the diagnostics contract and
environment checks. Reuse existing `ServerSettings` values and pass an explicit public-surface contract from `server.py`
to avoid introspecting FastMCP internals inside the domain module.

The public response is agent-legible and stable:

- `status`: `ok`, `warning`, or `error`;
- `checks`: ordered check records with `status`, `code`, `message`, and optional `details`;
- `warnings`: human-readable but concise warning strings;
- `next_actions`: concrete remediation steps;
- `environment`: normalized paths, retention limits, package version, and write-probe state.

The guide resource mirrors this contract and tells a host to call `diagnose_environment` before preview rendering when a
user asks whether the MCP server is connected or why local previews do not work.

## Testing

Use TDD:

1. Add failing unit tests for successful diagnostics and missing allowed-root warnings.
2. Add failing server tests for the new tool, resource, and capabilities entries.
3. Add a failing golden MCP scenario that reads the guide and calls `diagnose_environment` through stdio.
4. Implement `diagnostics.py`, wire it into `server.py`, and update snapshots/docs.

Release verification must run pytest, ruff, format check, ty, golden evals, release-version guard, build, tag push, CI
watch, and post-release publication checks.
