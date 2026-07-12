# Claude Desktop MCPB Design

## Goal

Ship AlbumentationsX MCP as an official MCP Bundle (`.mcpb`) that installs in Claude Desktop, including Free-plan Chat,
while preserving the server's bounded local filesystem policy and keeping Claude Code evidence separate.

## Context

The legacy `claude_desktop_config.json` path was exercised on 2026-07-12. Claude Desktop launched the configured
stdio process, then shut it down when its local-agent OAuth request was rejected because Claude Code requires a paid
plan. This is useful setup evidence, but it is not a successful host replay.

Current Anthropic guidance treats MCPB desktop extensions as the supported one-click mechanism for local MCP servers.
The official MCPB format supports a UV runtime, user-selected directories, manifest validation, and installation in
Claude Desktop without exposing a server to the public internet.

## Chosen Approach

Create a small UV-based wrapper bundle under `desktop-extension/`:

- `manifest.json` owns extension identity, user configuration, runtime metadata, and launch arguments.
- `pyproject.toml` pins the matching published `albumentationsx-mcp` version.
- `src/server.py` delegates directly to the package CLI, preserving one canonical MCP implementation.
- `icon.png` uses the same upstream Albumentations identity already published in `server.json`.
- `.mcpbignore` excludes local environments, caches, and build output.

The bundle will not fork server code or introduce a second protocol adapter.

## Alternatives Rejected

### Legacy desktop JSON

It enters the paid local-agent/Claude Code authentication path in the current Desktop build. Keeping it would create a
configuration that appears valid but is immediately shut down on a Free account.

### Remote custom connector

A remote connector works on Free, but it requires a publicly reachable HTTP endpoint. AlbumentationsX MCP reads local
datasets and emits local preview artifacts, so publishing that surface would weaken the current privacy and path-policy
model without product benefit.

### Vendored Python environment

Bundling a Python virtual environment would be platform-specific and large, especially with NumPy and OpenCV. The
official UV runtime handles compiled dependencies across supported platforms and keeps the bundle small.

## Security Model

Installation requires two explicit directory selections:

1. `allowed_directory`: the only root from which image and annotation inputs may be read.
2. `artifact_directory`: the only root where previews, manifests, and exports may be written.

Neither setting has a broad home-directory default. The manifest passes both values to the existing CLI flags, whose
resolved-path checks remain authoritative. A bounded numeric `max_preview_runs` setting maps to the existing retention
environment variable. The extension does not request API keys, network credentials, shell access, or remote services.

## Versioning And Distribution

The MCPB manifest version, its Python dependency pin, `pyproject.toml`, `server.json`, `.codex-plugin/plugin.json`, and
`.mcp.json` must agree for a release. A project-owned validator enforces this contract before packaging.

The release workflow will:

1. validate the manifest with the project validator and pinned official MCPB CLI;
2. pack `desktop-extension/` into `mcpb-dist/albumentationsx-mcp-X.Y.Z.mcpb`;
3. upload it as a separate workflow artifact;
4. publish only `dist/*` to PyPI;
5. attach both Python artifacts and the MCPB artifact to the GitHub Release.

This separation prevents `uv publish` from receiving a non-Python file.

## Host Acceptance

Before release, install a development bundle in Claude Desktop Free and perform a reviewer-observed bounded replay over
the existing generated 160 x 120 fixture:

1. confirm the extension and tools are visible;
2. read the client-smoke resource and call `run_host_smoke_check`;
3. build a review packet for the exact image path;
4. render and inspect a baseline;
5. record concrete feedback, adjust, rerender, and compare;
6. accept or reject with rationale and export only reviewed output.

The receipt may include sanitized run identifiers, package versions, contact sheets, and hashes. It must not include
account identifiers, raw chat transcripts, credentials, absolute private paths, or claims of external beta/adoption.

## Evidence Semantics

The new host is named `Claude Desktop`, not `Claude Code`. A successful Desktop replay adds independent host coverage
but does not alter the existing blocked Claude Code record. Product and release reports must preserve both facts.

## Testing

- Unit tests cover manifest/version/path-policy invariants and wrapper delegation.
- Existing project scaffolding tests cover release artifact separation.
- The official MCPB CLI validates and packs the bundle.
- Archive inspection verifies expected files and excludes caches or secrets.
- Full pytest, Ruff, formatting, `ty`, release readiness, and golden evals remain required.
- Manual host evidence is recorded only after the real Desktop UI completes the workflow.

## Non-Goals

- Hosting a remote MCP endpoint.
- Reimplementing the Python server in Node.js.
- Marking Claude Code as passed.
- Treating a generated fixture as beta or adoption evidence.
- Submitting to Anthropic's public extension directory before local installation and release automation are proven.
