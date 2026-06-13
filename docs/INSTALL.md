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
uvx --from albumentationsx-mcp==0.13.0 albumentationsx-mcp --help
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

Claude Desktop-style hosts use a JSON `mcpServers` object. Start with
[examples/claude_desktop_pypi_config.json](../examples/claude_desktop_pypi_config.json):

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

For preview work, add bounded roots:

```json
{
  "mcpServers": {
    "albumentationsx": {
      "command": "uvx",
      "args": [
        "--from",
        "albumentationsx-mcp",
        "albumentationsx-mcp",
        "--allowed-root",
        "/absolute/path/to/images",
        "--artifact-root",
        "/absolute/path/to/albu-artifacts"
      ]
    }
  }
}
```

Restart the host after editing its MCP configuration.

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

## Codex

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
uvx --from albumentationsx-mcp==0.13.0 albumentationsx-mcp --help
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

## Troubleshooting

- If the host cannot start the server, run the same `uvx` or `uv run` command manually and fix terminal errors first.
- If a local image path is rejected, confirm it is under `--allowed-root` or `ALBU_MCP_ALLOWED_ROOTS`.
- If preview reports lack thumbnails, confirm the artifact root still contains the preview run and contact sheet files.
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
