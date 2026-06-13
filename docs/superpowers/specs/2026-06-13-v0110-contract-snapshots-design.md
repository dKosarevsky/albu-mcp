# v0.11 Contract Snapshots Design

## Context

`v0.10.0` completed the core preview tuning loop and documented that `v1.0.0` should wait for contract hardening. The
next useful intermediate step is not another user-facing tool. It is a guardrail that makes accidental MCP surface
changes visible before release.

## Goals

- Add a canonical MCP contract snapshot for public tools, resources, and prompts.
- Keep contract export as development tooling, not runtime domain logic.
- Make snapshot diffs deterministic: sorted names, sorted JSON keys, stable indentation, and no environment-specific
  paths.
- Document how maintainers should handle compatible additions, breaking changes, and deprecations.
- Release this as `v0.11.0` if verification and publication checks pass.

## Non-Goals

- No new MCP tools, resources, prompts, or response fields.
- No registry schema changes beyond the package version.
- No generated docs site.
- No automatic semantic-version decision engine.

## Architecture

Create `scripts/export_mcp_contract.py` as the single contract exporter. It imports `create_mcp_server`, reads the
FastMCP registrations that the existing tests already inspect, and emits a compact JSON document:

- server name;
- public tools with name, description, and input schema;
- public resource URI templates with names and descriptions when available;
- public prompts with name, description, and argument schema when available.

Add `tests/fixtures/snapshots/mcp_contract.json` as the reviewed public contract fixture. Add a pytest test that compares
the current exporter output to that fixture. A tool/resource/prompt change is then either a deliberate snapshot update
with release notes or a failed test.

Add `docs/COMPATIBILITY.md` to define the project policy:

- compatible additions are allowed in minor releases;
- breaking removals or required input changes wait for a major release;
- behavior changes that alter user-visible recommendations, reports, or safety boundaries need changelog notes and golden
  eval coverage.

## Verification

The release is valid only if the contract snapshot test, full pytest suite, ruff, format check, ty, golden evals,
release version guard, build, CI, PyPI smoke, and MCP Registry publish all pass.
