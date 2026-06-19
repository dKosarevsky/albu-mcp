# V1 Readiness Audit

This audit records the release gate for `v1.0.0`. It is intentionally focused on public MCP compatibility and release
reproducibility. No runtime API changes are introduced by this pass.

## Public Contract Freeze

The public MCP contract is frozen for `v1.0.0`:

- tool names, descriptions, and input schemas are treated as stable;
- resource URIs and resource template parameters are treated as stable;
- prompt names and arguments are treated as stable;
- documented response fields are treated as stable;
- `server.json` package identity remains `io.github.dKosarevsky/albu-mcp`;
- the PyPI package identity remains `albumentationsx-mcp`.

Future compatible additions can ship in minor releases. Breaking changes require a major release unless needed to fix
unsafe or unusable behavior.

## Snapshot Guards

Two reviewed fixtures guard the public surface:

- `tests/fixtures/snapshots/mcp_contract.json` for tools, resources, resource templates, and prompts;
- `tests/fixtures/snapshots/output_contracts.json` for representative recipe, scoring, feedback, and report payloads.

Before cutting `v1.0.0`, regenerate both snapshots to temporary files and confirm there is no diff from committed
fixtures. Current CI and release jobs enforce this with `uv run python scripts/check_contract_snapshots.py`.

## Golden Evals

`evals/golden_mcp_scenarios.yaml` covers the host workflows that motivated the project:

- client smoke resource discovery and host preflight;
- diagnostics resource discovery and remediation checks;
- recipe recommendation, validation, explanation, and export;
- preview lifecycle operations;
- batch preview comparison;
- quality tuning session summary;
- MCP-native first-preview smoke using `albumentationsx://examples/first-preview` and `run_first_preview_review`;
- real sample first-preview smoke using `run_host_smoke_check`, `validate_preview_request`, `render_preview_batch`,
  manifest reads, candidate comparison, quality metrics, and cleanup.

Run `uv run python scripts/run_golden_evals.py` before every release.

## Release Automation

The release workflow builds the package, checks release metadata, runs tests, runs lint/type checks, executes golden MCP
evals, publishes to PyPI through Trusted Publishing, creates a GitHub Release, and runs a post-release `uvx` smoke check.

`uv run python scripts/check_release_readiness.py --tag v1.0.0` aggregates the fast release guards: version metadata,
manual host evidence schema, generated host acceptance evidence, and public contract snapshots.

The MCP Registry workflow publishes `server.json` metadata through GitHub OIDC after the PyPI package is visible.

## Install Flow

The canonical install path is:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
```

`docs/INSTALL.md` documents PyPI, MCP Registry, Claude Desktop, Claude Code, Cursor, Codex, bounded local roots, first
preview validation, smoke checks, troubleshooting, and safety notes.

## Compatibility Policy

`docs/COMPATIBILITY.md` defines compatible changes, breaking changes, deprecations, and required coverage. For `v1.0.0`,
that policy is part of the public maintenance contract.

## Decision

`v1.0.0` can be released when:

- snapshot regeneration shows no public contract drift;
- local tests, lint, formatting, type checks, golden evals, version guard, and build pass;
- GitHub CI and Release workflows pass;
- PyPI, PyPI Simple API, MCP Registry, GitHub Release, and `uvx` smoke confirm the published `v1.0.0` package.
