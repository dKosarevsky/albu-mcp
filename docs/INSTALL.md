# Install AlbumentationsX MCP

This guide covers the common MCP host setup paths for AlbumentationsX MCP. Prefer the published PyPI package unless you
are developing the server itself.

## Recommended Path

Use the published package through `uvx`:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
```

This matches the package advertised in [server.json](../server.json) and the public
[MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp) entry.

## PyPI

The Python package is published as
[albumentationsx-mcp](https://pypi.org/project/albumentationsx-mcp/). A host can launch it with:

```json
{
  "mcpServers": {
    "albumentationsx": {
      "command": "uvx",
      "args": ["--from", "albumentationsx-mcp", "albumentationsx-mcp"]
    }
  }
}
```

Pin a version when debugging or reproducing a release:

```bash
uvx --from albumentationsx-mcp==1.16.0 albumentationsx-mcp --help
```

## MCP Registry

The server is published under:

```text
io.github.dKosarevsky/albu-mcp
```

The registry package type is `pypi`, transport is `stdio`, and ownership is verified through the README
`mcp-name` marker. Keep [server.json](../server.json), [README.md](../README.md), and the PyPI package version in sync for
every release.

## Bounded Local Access

Preview rendering reads local images and writes generated artifacts. Scope both sides explicitly:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp \
  --allowed-root /absolute/path/to/images \
  --artifact-root /absolute/path/to/albu-artifacts
```

Use the smallest useful `--allowed-root`, usually a sampled review folder rather than a whole dataset. Keep
`--artifact-root` outside source datasets so cleanup and report generation cannot overwrite training data.

Environment variables are also supported:

```bash
ALBU_MCP_ALLOWED_ROOTS=/absolute/path/to/images \
ALBU_MCP_ARTIFACT_ROOT=/absolute/path/to/albu-artifacts \
uvx --from albumentationsx-mcp albumentationsx-mcp
```

Use `ALBU_MCP_MAX_PREVIEW_RUNS` to adjust preview index retention. The default keeps the latest 100 preview runs.

## Claude Desktop

Use the versioned release artifact rather than editing Claude's JSON configuration:

1. Download `albumentationsx-mcp-<version>.mcpb` from the matching
   [GitHub Release](https://github.com/dKosarevsky/albu-mcp/releases).
2. In Claude Desktop, open **Settings → Extensions → Advanced settings**.
3. Under **Extension Developer**, choose **Install Extension…** and select the `.mcpb` file.
4. Select the smallest useful image/annotation directory for **Allowed image directory**.
5. Select a separate output directory for **Preview artifact directory** and keep the default retention unless a bounded
   value from 1 to 500 is needed.
6. Open **+ → Connectors** in a chat and confirm that **AlbumentationsX MCP** and its tools are available.

The extension runs locally through Claude Desktop's managed UV runtime and delegates to the matching published PyPI
package. It does not require Claude Code or a manual Python installation. It has no implicit home-directory access: the
two selected directories become the only read and write roots passed to the server.

Privately distributed extensions must be updated by installing the newer `.mcpb` release. If installation is disabled by
an organization policy, ask the administrator to allow the extension; do not work around the policy with broader roots.

### Portable JSON fallback

Other desktop hosts that support a Claude-style `mcpServers` object can still use
[examples/claude_desktop_pypi_config.json](../examples/claude_desktop_pypi_config.json). For bounded previews, use
[examples/claude_desktop_preview_config.json](../examples/claude_desktop_preview_config.json), replace both placeholder
paths, and restart that host after editing its MCP configuration. Current Claude Desktop users should prefer the MCPB
extension above.

Maintainers can validate and build the same release artifact with Node.js 20 or newer:

```bash
uv run python scripts/check_desktop_extension.py
uv run python -m scripts.build_desktop_extension --output-dir dist/mcpb
```

## Claude Code

Claude Code can import a stdio JSON config directly:

```bash
claude mcp add-json albumentationsx \
  '{"type":"stdio","command":"uvx","args":["--from","albumentationsx-mcp","albumentationsx-mcp"]}'
```

With bounded roots:

```bash
claude mcp add-json albumentationsx \
  '{"type":"stdio","command":"uvx","args":["--from","albumentationsx-mcp","albumentationsx-mcp","--allowed-root","/absolute/path/to/images","--artifact-root","/absolute/path/to/albu-artifacts"]}'
```

The same command is available in
[examples/claude_code_preview_command.md](../examples/claude_code_preview_command.md).

Then verify from Claude Code:

```bash
claude mcp get albumentationsx
claude mcp list
```

## Cursor

Cursor-style MCP JSON can use the same published package command. Start with
[examples/cursor_mcp_config.json](../examples/cursor_mcp_config.json):

```json
{
  "mcpServers": {
    "albumentationsx": {
      "command": "uvx",
      "args": ["--from", "albumentationsx-mcp", "albumentationsx-mcp"]
    }
  }
}
```

If the host supports project-level MCP configs, commit only non-secret config. Keep local machine paths in a user-level or
ignored config when they are specific to your workstation.

For preview work, use
[examples/cursor_preview_mcp_config.json](../examples/cursor_preview_mcp_config.json) and replace the placeholder roots.

## Codex

### Native plugin bundle

The repository root is a native Codex plugin source through [`.codex-plugin/plugin.json`](../.codex-plugin/plugin.json)
and [`.mcp.json`](../.mcp.json). Adding that trusted checkout through the local or team plugin controls supported by
your Codex installation loads the canonical skill and the pinned base MCP server together. This is a source bundle,
not a public Codex marketplace listing.

The bundle starts the published package with `cwd` fixed to the plugin directory, so it does not grant a user dataset
root by default. The server's fallback allowed root and `artifacts/` directory stay inside that plugin source. For
preview work, set these in the environment that launches Codex:

```bash
export ALBU_MCP_ALLOWED_ROOTS=/absolute/path/to/images
export ALBU_MCP_ARTIFACT_ROOT=/absolute/path/to/albu-artifacts
export ALBU_MCP_MAX_PREVIEW_RUNS=100
```

Restart Codex after installing the plugin or changing these values, then call `run_host_smoke_check`. Confirm its
`allowed_roots` contains the intended dataset root and `preview_ready` is true before rendering.
Direct TOML configuration remains the fallback for builds without local plugin sources and project-specific roots.

Maintainers can validate bundle structure, permissions, and version pinning with:

```bash
uv run python scripts/check_codex_plugin.py
```

### Direct TOML

Codex-style TOML configs can use [examples/codex_mcp_config.toml](../examples/codex_mcp_config.toml):

```toml
[mcp_servers.albumentationsx]
command = "uvx"
args = ["--from", "albumentationsx-mcp", "albumentationsx-mcp"]
```

Bounded local access uses the same args:

```toml
[mcp_servers.albumentationsx]
command = "uvx"
args = [
  "--from",
  "albumentationsx-mcp",
  "albumentationsx-mcp",
  "--allowed-root",
  "/absolute/path/to/images",
  "--artifact-root",
  "/absolute/path/to/albu-artifacts",
]
```

The same preview-ready shape is available in
[examples/codex_preview_mcp_config.toml](../examples/codex_preview_mcp_config.toml).

## First Preview Workflow

After configuring Claude Desktop, Claude Code, Cursor, or Codex, use the same first-preview flow:

1. Read `albumentationsx://examples/client-smoke` when the host exposes resource reads; otherwise call
   `run_host_smoke_check` directly.
2. If the resource was read, call `run_host_smoke_check` next.
3. Continue only when `preview_ready` is true.
4. Copy `preview_request_template.request` and replace the placeholder image path.
5. Call `validate_preview_request`.
6. Call `render_preview_batch` only when the request is valid.

The copyable prompt is in [examples/first_preview_workflow.md](../examples/first_preview_workflow.md).
MCP-native hosts can also read `albumentationsx://examples/first-preview` or use the `run_first_preview_review` prompt.
For the common robustness loop where a user rejects one noisy preview, read
`albumentationsx://examples/distortion-review` or copy [examples/distortion_review_workflow.md](../examples/distortion_review_workflow.md).

## Local Checkout

Use a checkout only when changing or testing the server:

```bash
git clone https://github.com/dKosarevsky/albu-mcp.git
cd albu-mcp
uv sync --all-extras --dev
uv run albumentationsx-mcp --help
```

JSON-configured hosts can launch the checkout with:

```json
{
  "mcpServers": {
    "albumentationsx": {
      "command": "uv",
      "args": ["run", "albumentationsx-mcp"],
      "cwd": "/absolute/path/to/albu-mcp"
    }
  }
}
```

## Smoke Check

Before wiring a host, verify the command works in a terminal:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp --help
```

For a pinned release:

```bash
uvx --from albumentationsx-mcp==1.16.0 albumentationsx-mcp --help
```

For local development:

```bash
uv run albumentationsx-mcp --help
uv run python scripts/run_golden_evals.py
```

Expected CLI output includes:

```text
usage: albumentationsx-mcp [-h] [--transport {stdio,streamable-http}]
                           [--artifact-root ARTIFACT_ROOT]
                           [--allowed-root ALLOWED_ROOT]
```

After wiring a host, ask it to read `albumentationsx://examples/client-smoke` when the host exposes resource reads;
otherwise call `run_host_smoke_check` directly. The resource provides the detailed client smoke playbook, while the
tool response contains the complete safe fallback guidance. A healthy host smoke report returns `preview_ready: true`,
`workflow_guidance`, and a `preview_request_template`. After replacing the sample path, call `validate_preview_request`
before `render_preview_batch`.

If the host connects but previews fail, ask it to read `albumentationsx://diagnostics/guide` and call
`diagnose_environment`. The report checks AlbumentationsX import/version, `--allowed-root`, `--artifact-root`,
artifact writeability, and the public MCP surface. A healthy setup returns `status: "ok"`, check-level `severity`, and
structured `remediation_actions` plus text `next_actions`.

## Troubleshooting

- If the host connects but preview rendering fails, call `run_host_smoke_check` first, then inspect
  `diagnose_environment` details if `preview_ready` is false.
- If the host cannot start the server, run the same `uvx` or `uv run` command manually and fix terminal errors first.
- If a filled preview request fails, call `validate_preview_request` and follow its `remediation_actions`.
- If a local image path is rejected, confirm it is under `--allowed-root` or `ALBU_MCP_ALLOWED_ROOTS`.
- If `diagnose_environment` reports remediation code `fix_allowed_root`, restart the host with an existing absolute
  `--allowed-root`.
- If it reports `fix_artifact_root` or `fix_artifact_permissions`, restart with a writable `--artifact-root` outside
  source datasets.
- If it reports `refresh_host_surface`, restart the host after upgrading or clearing stale MCP tool discovery.
- If preview reports lack thumbnails, confirm the artifact root still contains the preview run and contact sheet files.
- If host-side tool discovery looks incomplete and the host exposes resource reads, read
  `albumentationsx://examples/client-smoke` and `albumentationsx://capabilities`; otherwise call
  `run_host_smoke_check` directly and inspect its checks.
- If a host shows stale tools after upgrading, restart the host and clear any client-side MCP server cache it provides.
- If `uvx` cannot find a just-published version, wait for PyPI Simple API propagation and retry with
  `--refresh-package albumentationsx-mcp`.
- If JSON config fails to parse, validate that all paths are absolute strings and that Windows paths use escaped
  backslashes or forward slashes.

## Safety Notes

- Install from the official PyPI package or this repository.
- Review MCP startup commands before approving them in a host.
- Scope `--allowed-root` to the smallest review folder needed for the session.
- Keep generated artifacts separate from source datasets and training outputs.
- Do not put API keys or private paths into committed project-level MCP config.
- Treat preview quality findings as review prompts; the user still decides whether an augmentation is acceptable.
