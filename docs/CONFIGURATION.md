# Configuration

AlbumentationsX MCP runs locally and exposes one canonical MCP surface through an optional capability profile. The
default remains `full`; selecting a focused profile only changes what the host discovers.

## Local Paths

Set the smallest useful read root and a separate artifact directory:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp \
  --allowed-root /absolute/path/to/images \
  --artifact-root /absolute/path/to/albu-artifacts
```

The equivalent environment settings are:

```bash
export ALBU_MCP_ALLOWED_ROOTS=/absolute/path/to/images
export ALBU_MCP_ARTIFACT_ROOT=/absolute/path/to/albu-artifacts
export ALBU_MCP_MAX_PREVIEW_RUNS=100
```

Separate multiple allowed roots in `ALBU_MCP_ALLOWED_ROOTS` with the platform path separator. CLI path options override
their environment equivalents. The retention limit always comes from `ALBU_MCP_MAX_PREVIEW_RUNS`; its default is 100.

## Capability Profiles

Use `--capability-profile` or `ALBU_MCP_CAPABILITY_PROFILE`:

| Profile | Intended workflow | Surface |
| --- | --- | --- |
| `core` | Discovery and pipeline design without local preview tools | Catalog, validation, recommendation, adjustment, explanation, export, diagnostics, smoke, and workflow fallback |
| `review` | Preview, reject, adjust, compare, accept, and export | `core` plus rendering, comparison, feedback, ranking, reports, sessions, and review prompts |
| `dataset` | Bounded local dataset planning, preview, and quality inspection | `core` plus onboarding, review packets, quality inspection, validation, batch rendering, feedback recording, comparison, reports, and dataset candidate scoring |
| `full` | Every supported workflow | Complete canonical surface; default for all v1.x installations |

For a preview-focused host:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp \
  --capability-profile review \
  --allowed-root /absolute/path/to/images \
  --artifact-root /absolute/path/to/albu-artifacts
```

Or use the environment:

```bash
ALBU_MCP_CAPABILITY_PROFILE=review \
uvx --from albumentationsx-mcp albumentationsx-mcp
```

The CLI option overrides the environment profile. Unknown values fail before server startup and list `core`, `review`,
`dataset`, and `full`. Restart the MCP server after changing a profile so the host refreshes tool discovery.

Focused profiles are filtered, dependency-closed views of the same registration manifest used by `full`; they are not
separate implementations. `albumentationsx://capabilities` reports the active profile and only the tools, prompts, and
workflow resources available in that view.

`core` intentionally has no local preview tools. Its smoke report can confirm a healthy installation, but returns
`preview_ready=false` with a `--capability-profile review` action. `review`, `dataset`, and `full` expose the validation
and batch-render tools required for `preview_ready=true`.

`review`, `dataset`, and `full` also expose `record_preview_feedback`, so every action in the Preview Review MCP App is
available wherever its render surface is published. `dataset` intentionally omits the broader tuning-session tools.

The MCPB, Registry metadata, plugin bundle, and existing configuration examples omit the option and therefore retain
the `full` profile. Changing that default requires a future major release.

## Resource-Read Fallback

Some MCP hosts list resources but do not expose resource reads to the model. Use the additive tool fallback:

```text
get_workflow_example(example_id="client-smoke")
```

The closed identifier set is:

- `client-smoke`
- `first-preview`
- `distortion-review`
- `dataset-onboarding`
- `diagnostics`
- `review-loop`
- `report-handoff`

The tool returns the exact reviewed resource payload when the corresponding example resource is exposed by the active
profile. `client-smoke` reflects the active profile: in `core` it expects `preview_ready=false` and recommends a
preview-capable profile. If a requested resource is intentionally outside the profile, the tool fails with the profile
name and required URI instead of returning steps for unavailable tools. `full` exposes all seven examples.

After reading an available example through either path, call `run_host_smoke_check`. Its
`workflow_guidance.fallback_tool` field contains the canonical fallback call, and preview-capable profiles return the
same preview template without a model-visible resource read. The server never infers host capabilities and performs no
remote reads.

## Transport

The default transport is `stdio`. Local HTTP can be selected explicitly:

```bash
albumentationsx-mcp --transport streamable-http
```

Path policy, profile filtering, and artifact retention are identical across transports.
