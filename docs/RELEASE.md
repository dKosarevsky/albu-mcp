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

1. Update `CHANGELOG.md` with user-facing changes and the release date.
2. Update `version` in `pyproject.toml`.
3. Update `version` in `server.json` and `packages[0].version`.
4. Run the local quality gate:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/validate_host_manual_runs.py
uv run python scripts/check_host_acceptance_report.py
uv run python scripts/run_golden_evals.py
uv build
```

5. Commit the version bump:

```bash
git add pyproject.toml server.json uv.lock README.md CHANGELOG.md docs/INSTALL.md docs/V1_READINESS.md
git commit -m "chore: release vX.Y.Z"
```

## GitHub Release

Create and push a `vX.Y.Z` tag:

```bash
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

The `Release` workflow runs in three stages:

1. `build`: runs the quality gate, builds the wheel/source distribution, and uploads `dist/*` as a workflow artifact.
2. `publish-pypi`: waits for the protected GitHub environment `pypi`, then publishes the same artifact to PyPI through
   Trusted Publishing.
3. `github-release`: creates the GitHub Release and attaches the same `dist/*` artifact.

## PyPI Package Publishing

The release workflow publishes the underlying Python package with:

```bash
uv publish --trusted-publishing automatic dist/*
```

This uses PyPI Trusted Publishing through GitHub OIDC. Do not create long-lived PyPI API tokens for the release workflow.

Once the package is published, users can run the server package with:

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

The release workflow publishes MCP Registry metadata automatically after the PyPI smoke check succeeds. Keep the manual
workflow for metadata repair runs. A scheduled watchdog also checks that the public Registry latest entry stays active
and matches [server.json](../server.json).

## Post-Release Checks

Verify package execution:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp --help
```

Verify MCP Registry metadata:

```bash
uv run python scripts/check_mcp_registry_status.py
```

Export reviewable host acceptance evidence:

```bash
uv run python scripts/record_host_manual_run.py --host Codex --status passed --date 2026-06-19 \
  --evidence "Codex app listed tools, read workflow resources, and ran run_host_smoke_check."
uv run python scripts/validate_host_manual_runs.py
uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md
uv run python scripts/check_host_acceptance_report.py
```

This artifact records automated release coverage and keeps manual host UI status pending until a reviewer adds dated
host-specific evidence to `docs/HOST_MANUAL_RUNS.json`. The record shape is documented in
`docs/HOST_MANUAL_RUNS.schema.json`.
