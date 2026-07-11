# Codex Plugin Bundle Design

## Goal

Package the existing AlbumentationsX MCP server and agent skill as one validated Codex plugin source so a Codex
installation can discover both components together. Preserve the current least-privilege filesystem model and keep
the published PyPI package as the MCP runtime source of truth.

## Observed Problem

The repository skill can be installed independently from `skills.sh`, while the MCP server still requires a separate
host configuration. In a real Codex workspace audit on 2026-07-11, the AlbumentationsX skill was discoverable but no
AlbumentationsX MCP tools or resources were exposed by the host. This prevents the first host smoke check even though
the operator guidance is present.

## Options Considered

### Keep manual host configuration

This adds no maintenance cost, but preserves the observed split between guidance and executable tools. It remains the
portable fallback for non-Codex hosts, not the preferred Codex packaging path.

### Add a config-mutating installer

A CLI command could edit a user's Codex configuration. This would be host-version-sensitive, require backup and merge
semantics, and introduce a broad local side effect. It is not justified while Codex has a native plugin contract.

### Add a native Codex plugin bundle

This is the selected approach. The repository root becomes a valid plugin source through a manifest and companion MCP
configuration. It reuses the canonical `skills/` tree and starts the pinned published package through `uvx`.

## Architecture

### Plugin manifest

`.codex-plugin/plugin.json` declares:

- plugin identity and semantic version;
- the existing `./skills/` directory;
- the companion `./.mcp.json` file;
- concise Codex UI metadata and starter prompts;
- repository, documentation, author, and license metadata.

The plugin version must equal the version in `pyproject.toml`.

### MCP companion configuration

`.mcp.json` declares one stdio server named `albumentationsx`. It runs:

```text
uvx --from albumentationsx-mcp==<project-version> albumentationsx-mcp
```

The package is pinned so plugin behavior is reproducible. The configuration passes through only these documented,
non-secret environment variables when the host provides them:

- `ALBU_MCP_ALLOWED_ROOTS`
- `ALBU_MCP_ARTIFACT_ROOT`
- `ALBU_MCP_MAX_PREVIEW_RUNS`

The MCP process sets `cwd` to `.` so the host resolves the fallback working directory inside the installed plugin,
never the user's workspace. Without explicit environment values, the current server therefore limits its fallback
allowed root and artifact directory to plugin-owned files. It does not receive a user dataset root. Operators must
confirm that smoke-check `allowed_roots` contains their intended dataset root before any preview, even when
`preview_ready` is true.

### Validation boundary

A focused `scripts/check_codex_plugin.py` owns the repository contract. It validates structural metadata, canonical
paths, the pinned command, plugin-root working directory, environment pass-through, absence of implicit user dataset
roots, and version consistency.
The existing release-readiness aggregate invokes this guard, so CI and tagged releases cannot silently drift.

The project test suite also checks the public documentation and canonical skill relationship. Local development may
additionally run the Codex plugin creator validator, but CI does not depend on files outside this repository.

## User Experience

README keeps `uvx` as the universal quick start and adds one short Codex plugin note. `docs/INSTALL.md` explains:

1. what the bundle includes;
2. that plugin installation loads both the skill and base MCP server;
3. how bounded preview roots are supplied through documented environment variables;
4. that the host must be restarted and `run_host_smoke_check` must confirm both the intended root and `preview_ready`;
5. that direct TOML configuration remains the explicit fallback and the route for per-project roots.

Documentation must not claim a public Codex marketplace listing until one exists.

## Testing

- Contract tests parse both JSON files and assert their exact security-sensitive fields.
- Parametrized tests reject plugin-version drift, unpinned packages, extra environment variables, workspace cwd,
  implicit dataset-root args, and missing canonical skill/MCP paths.
- Release-readiness tests require the new guard and verify failures are surfaced without hiding other checks.
- The existing skill, documentation, full pytest, Ruff, formatting, ty, build, MCP smoke, and release gates remain green.
- The official local Codex plugin validator is run against the repository root as an additional integration check.

## Non-Goals

- Publishing to a public Codex marketplace.
- Editing user-level Codex configuration.
- Granting a user dataset root automatically.
- Replacing PyPI, MCP Registry, `skills.sh`, or non-Codex host instructions.
- Counting plugin validation or local MCP smoke output as real host or beta evidence.
