# AlbumentationsX MCP for Claude Desktop

This directory is the source of the official UV-based Claude Desktop extension for
[AlbumentationsX MCP](https://github.com/dKosarevsky/albu-mcp).

The extension delegates to the matching published Python package. Installation asks
for two explicit local directories: one read root for images and annotations, and one
write root for generated previews and exports. No home-directory or filesystem-wide
default is granted.

Validate the source contract from the repository root:

```console
uv run python scripts/check_desktop_extension.py
```

The packaged `.mcpb` artifact is built by the release workflow. Do not add credentials,
datasets, generated previews, or a virtual environment to this directory.
