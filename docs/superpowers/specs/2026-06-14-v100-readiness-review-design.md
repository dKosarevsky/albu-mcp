# v1.0 Readiness Review Design

## Context

`v0.13.0` completed the host-facing install guide. The MCP server now has:

- stable public tool, resource, prompt, and package metadata snapshots;
- representative output contract snapshots;
- golden MCP evals for end-to-end host workflows;
- PyPI Trusted Publishing and MCP Registry publishing;
- install guidance for common local stdio host setups.

The remaining v1 decision should be based on evidence that these contracts are intentionally frozen and that release
metadata no longer presents the package as alpha.

## Scope

This pass does not change runtime behavior or the MCP contract. It will:

- add a `docs/V1_READINESS.md` audit with explicit pass/fail criteria;
- update release documentation examples from old `v0.1.0` values to version-neutral `vX.Y.Z` commands;
- update package maturity metadata from alpha to production/stable for the v1 release;
- add tests that require the v1 readiness audit, stable classifier, release guide hygiene, and unchanged snapshot guard
  documentation;
- run contract/output snapshot export checks and fail if regenerated snapshots differ from committed fixtures;
- if all checks pass, release `v1.0.0`.

Out of scope:

- adding, removing, or renaming MCP tools/resources/prompts;
- changing response shapes;
- changing artifact URI semantics, allowed-root behavior, or retention behavior;
- adding remote HTTP deployment guidance.

## Design

`docs/V1_READINESS.md` is the human-readable release gate. It records:

- current public contract status;
- snapshot guard status;
- golden eval status;
- packaging and registry status;
- install guide status;
- known compatibility policy for future changes.

The tests in `tests/test_project_scaffolding.py` become the automation layer that keeps the audit honest. They should not
try to prove every behavior; that is already covered by focused tests, snapshots, and golden evals. They should prove the
v1 gate is present and not contradicted by obvious metadata or documentation drift.

The release commit updates `pyproject.toml`, `server.json`, `uv.lock`, `README.md`, `CHANGELOG.md`, and the pinned
version examples in `docs/INSTALL.md` from `0.13.0` to `1.0.0`.

## Release Decision

Cut `v1.0.0` only if:

- full local verification passes;
- `scripts/export_mcp_contract.py` regenerates the same MCP surface snapshot;
- `scripts/export_output_contracts.py` regenerates the same representative output snapshot;
- GitHub CI and Release workflows pass;
- PyPI, PyPI Simple API, MCP Registry, GitHub Release, and `uvx` smoke all confirm `1.0.0`.
