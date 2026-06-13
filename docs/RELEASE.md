# Release and MCP Registry Publishing

This project is a Python MCP stdio server. The community publishing model has two distinct layers:

- **PyPI** hosts the installable Python package with the server code.
- **MCP Registry** hosts `server.json` metadata that tells MCP clients and downstream registries where the package lives
  and how to run it.

Tools are not published separately. They are runtime capabilities exposed by the server after an MCP host starts it.

## Registry Identity

The public MCP Registry name is:

```text
io.github.dKosarevsky/albu-mcp
```

For PyPI ownership verification, `README.md` includes:

```html
<!-- mcp-name: io.github.dKosarevsky/albu-mcp -->
```

The same name must match `server.json`.

## Version Bump

1. Update `version` in `pyproject.toml`.
2. Update `version` in `server.json` and `packages[0].version`.
3. Run the local quality gate:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv build
```

4. Commit the version bump:

```bash
git add pyproject.toml server.json uv.lock
git commit -m "chore: release v0.1.0"
```

## GitHub Release

Create and push an annotated tag:

```bash
git tag -a v0.1.0 -m "v0.1.0"
git push origin main
git push origin v0.1.0
```

The `Release` workflow builds the wheel and source distribution, runs the quality gate, and creates a GitHub Release with
`dist/*` attached.

## PyPI Package Publishing

After a PyPI trusted publisher is configured for this repository, publish the underlying Python package with:

```bash
uv publish --trusted-publishing automatic dist/*
```

Once published, users can run the server package with:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
```

## MCP Registry Publishing

After the PyPI package is available, publish MCP discovery metadata:

```bash
mcp-publisher login github
mcp-publisher publish
```

In CI, `.github/workflows/publish-mcp.yml` uses GitHub OIDC:

```bash
mcp-publisher login github-oidc
mcp-publisher publish
```

## Post-Release Checks

Verify package execution:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp --help
```

Verify MCP Registry metadata:

```bash
curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp"
```
