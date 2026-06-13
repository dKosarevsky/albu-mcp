# Release Process

This project ships as a Python package and as an MCP stdio server. Releases are tag-driven.

## Version Bump

1. Update `version` in `pyproject.toml`.
2. Run the local quality gate:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv build
```

3. Commit the version bump:

```bash
git add pyproject.toml uv.lock
git commit -m "chore: release v0.1.0"
```

## GitHub Release

Create and push an annotated tag:

```bash
git tag -a v0.1.0 -m "v0.1.0"
git push origin main
git push origin v0.1.0
```

The `Release` workflow builds the wheel and source distribution, runs the same quality gate, and creates a GitHub Release
with `dist/*` attached.

## PyPI Publishing

After a PyPI trusted publisher is configured for this repository, publish from the release workflow or locally with:

```bash
uv publish --trusted-publishing automatic dist/*
```

Once published, users can run the MCP server with:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
```

## Post-Release Check

Verify the published package in a clean environment:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp --help
```
