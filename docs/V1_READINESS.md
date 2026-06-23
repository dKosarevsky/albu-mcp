# V1 Readiness Audit

This audit records the release gate for a future `v1.0.0`. It is intentionally focused on public MCP compatibility,
host proof, and release reproducibility.

## Current Status

As of 2026-06-23, `v1.15.0` is the latest published pre-v1 release:

- PyPI package: `albumentationsx-mcp==1.15.0`;
- MCP Registry entry: active/latest for `io.github.dKosarevsky/albu-mcp`;
- GitHub release and PyPI Trusted Publishing completed for `v1.15.0`;
- machine-verifiable host proof status is tracked in `docs/HOST_PROOF_STATUS.md`;
- Manual Host UI evidence is still `pending` and must not be treated as passed until dated host screenshots or logs are
  recorded through the host proof sprint runbook.

The current product handoff for first real-dataset previews is `build_review_packet`. It combines dataset onboarding,
safe preview request validation, the review tool sequence, and `albumentationsx://examples/report-handoff`.

## Public Contract Freeze

The public MCP contract is not frozen yet. The intended `v1.0.0` freeze covers:

- tool names, descriptions, and input schemas are treated as stable;
- resource URIs and resource template parameters are treated as stable;
- prompt names and arguments are treated as stable;
- documented response fields are treated as stable;
- `server.json` package identity remains `io.github.dKosarevsky/albu-mcp`;
- the PyPI package identity remains `albumentationsx-mcp`.

Future compatible additions can ship in minor releases after v1. Breaking changes require a major release unless needed
to fix unsafe or unusable behavior.

## Snapshot Guards

Two reviewed fixtures guard the public surface:

- `tests/fixtures/snapshots/mcp_contract.json` for tools, resources, resource templates, and prompts;
- `tests/fixtures/snapshots/output_contracts.json` for representative recipe, scoring, feedback, and report payloads.

Before cutting `v1.0.0`, regenerate both snapshots to temporary files and confirm there is no diff from committed
fixtures. Current CI and release jobs enforce this with `uv run python scripts/check_contract_snapshots.py`.

`build_review_packet` is included in the MCP contract snapshot, and representative output for
`build_review_packet_ready` is included in the output contract snapshot.

## Golden Evals

`evals/golden_mcp_scenarios.yaml` covers the host workflows that motivated the project:

- client smoke resource discovery and host preflight;
- diagnostics resource discovery and remediation checks;
- recipe recommendation, validation, explanation, and export;
- preview lifecycle operations;
- batch preview comparison;
- quality tuning session summary;
- MCP-native first-preview smoke using `albumentationsx://examples/first-preview` and `run_first_preview_review`;
- distortion-review resource discovery for rejected noisy preview loops;
- Review Packet first-preview handoff via `review_packet_flow`;
- real sample first-preview smoke using `run_host_smoke_check`, `validate_preview_request`, `render_preview_batch`,
  manifest reads, candidate comparison, quality metrics, and cleanup.

Run `uv run python scripts/run_golden_evals.py` before every release.

## Release Automation

The release workflow builds the package, checks release metadata, runs tests, runs lint/type checks, executes golden MCP
evals, publishes to PyPI through Trusted Publishing, creates a GitHub Release, and runs a post-release `uvx` smoke check.

`uv run python scripts/check_release_readiness.py --tag v1.15.0` currently aggregates the fast release guards for the
latest pre-v1 tag: version metadata, manual host evidence schema, generated host acceptance evidence, first-10-minutes
entrypoints, host proof sprint entrypoints, and public contract snapshots.

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

`v1.0.0` should be cut only after:

- snapshot regeneration shows no public contract drift;
- local tests, lint, formatting, type checks, golden evals, version guard, and build pass;
- GitHub CI and Release workflows pass;
- PyPI, PyPI Simple API, MCP Registry, GitHub Release, and `uvx` smoke confirm the published package;
- Manual Host UI evidence for the target hosts is no longer `pending` and is recorded in the host proof artifacts;
- no open product blocker remains around `build_review_packet`, preview validation, report handoff, or registry install
  instructions.
