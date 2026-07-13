# MCP SDK v1 Dependency Bound Design

## Context

AlbumentationsX MCP 1.17.0 declares `mcp[cli]>=1.24.0` without an upper bound. The official MCP Python SDK is preparing
a breaking v2 release and recommends that v1 consumers add `<2`. A fresh `uvx` installation could otherwise resolve
an incompatible major version without any change to this project.

## Decision

Release `1.17.1` as a dependency-safety patch with `mcp[cli]>=1.24.0,<2`. Keep the current SDK, public MCP contract,
runtime behavior, and host workflows unchanged. The Claude Desktop wrapper continues to depend on the exact
`albumentationsx-mcp==1.17.1` package and therefore inherits the bound rather than duplicating it.

## Architecture

- `pyproject.toml` remains the single source of truth for direct runtime dependency bounds.
- A scaffolding test parses project metadata and requires both the supported v1 floor and the `<2` ceiling.
- Existing version guards keep PyPI, MCP Registry, Codex plugin, MCP config, and MCPB metadata synchronized.
- Release readiness, contract snapshots, and golden MCP scenarios must remain unchanged except for generated version
  references.

## Release Scope

The patch updates package and distribution metadata to `1.17.1`, adds one changelog entry, regenerates only current
version-bearing status documents, and publishes through the existing trusted release workflow. Historical release
receipts and old design documents remain immutable.

## Verification

- The dependency-bound test must fail against the current unbounded declaration and pass after the fix.
- Full pytest, Ruff, formatting, ty, release readiness for `v1.17.1`, golden MCP evals, package build, and MCPB build
  must pass.
- The release workflow must publish PyPI, GitHub Release assets, published-package smoke, and MCP Registry metadata.

## Non-Goals

- Migrating to MCP Python SDK v2.
- Adding MCP Apps or changing the public tool/resource/prompt surface.
- Rewriting host evidence or counting generated fixtures as beta evidence.
