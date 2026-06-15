# v1.3 Diagnostics Remediation Design

`diagnose_environment` in v1.2 returns useful setup checks, but host agents still have to parse human strings in
`next_actions`. v1.3 should make remediation machine-readable while keeping the v1.2 response shape compatible.

## Scope

Add compatible output fields:

- `DiagnosticCheck.severity`: machine-readable impact level for each check.
- `DiagnosticsReport.remediation_actions`: structured actions with stable codes, affected check codes, severity,
  summary, optional command hint, and docs resource URI.

Keep existing fields:

- `status`
- `checks`
- `warnings`
- `next_actions`
- `environment`

`next_actions` remains as a text list for existing hosts and is derived from the structured remediation actions.

## Contract

Severity values are intentionally small and stable:

- `info`: successful checks and proceed guidance;
- `medium`: warning-level setup issues such as a missing allowed root;
- `high`: local filesystem or MCP surface issues that block preview work;
- `critical`: package import failures that prevent the server from functioning.

Remediation action codes:

- `reinstall_package`: AlbumentationsX import/package issues;
- `fix_allowed_root`: invalid or missing preview input root;
- `fix_artifact_root`: artifact root cannot be created or is not a directory;
- `fix_artifact_permissions`: artifact write probe failed;
- `refresh_host_surface`: host sees stale or incomplete MCP tools/resources;
- `proceed_with_preview_smoke`: no blocking issue; continue with safe preview flow.

## Testing

Use TDD:

1. Add failing tests for severity on healthy, warning, and error checks.
2. Add failing tests for structured remediation actions and preserved `next_actions`.
3. Add representative diagnostics outputs to `scripts/export_output_contracts.py` and snapshot fixtures.
4. Verify full pytest, ruff, format check, ty, golden evals, release-version guard, build, CI, PyPI, and MCP Registry.

This is a public output contract addition, so release as `v1.3.0`.
