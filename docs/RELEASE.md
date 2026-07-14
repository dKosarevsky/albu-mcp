# Release and MCP Registry Publishing

This project is a Python MCP stdio server with three distribution layers:

- **PyPI** hosts the installable Python package with the server code.
- **MCP Registry** hosts `server.json` metadata that tells MCP clients and downstream registries where the package lives
  and how to run it.
- **GitHub Releases** host the installable Claude Desktop MCPB and its checksum.

Tools are not published separately. They are runtime capabilities exposed by the server after an MCP host starts it.

For stable v1 planning, use the generated release train checklist:
[docs/V1_RELEASE_TRAIN.md](V1_RELEASE_TRAIN.md).

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
4. Update `version` in `.codex-plugin/plugin.json` and the package pin in `.mcp.json`.
5. Update `version` in `desktop-extension/manifest.json`, `desktop-extension/pyproject.toml`, and the exact package pin in
   the desktop extension project.
6. Run `uv lock` so the local package version in `uv.lock` matches.
7. Run the local quality gate. Building the MCPB additionally requires Node.js 20 or newer:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/validate_host_manual_runs.py
uv run python scripts/check_host_acceptance_report.py
uv run python scripts/check_contract_snapshots.py
uv run python scripts/check_demo_assets.py --output-dir docs/assets/demo --check
uv run python scripts/check_desktop_extension.py
uv run python scripts/check_release_readiness.py --tag vX.Y.Z
uv run python scripts/extract_release_notes.py --tag vX.Y.Z
uv run python scripts/run_golden_evals.py
uv build
uv run python -m scripts.build_desktop_extension --output-dir dist/mcpb
```

If `check_contract_snapshots.py` reports drift, review its classification before updating fixtures. Use
`scripts/classify_contract_drift.py` as the structured snapshot drift classifier for ad hoc JSON snapshot comparisons.

Use `uv run python scripts/check_release_readiness.py --tag vX.Y.Z --format json` when another tool needs
machine-readable pre-release status. In GitHub Actions, the same guard writes a compact Markdown table to
`GITHUB_STEP_SUMMARY` automatically.
This release readiness guard aggregates manual host records, generated evidence freshness, contract snapshots, and
version consistency before tagging.

8. Commit the version bump:

```bash
git add pyproject.toml server.json .codex-plugin/plugin.json .mcp.json desktop-extension/manifest.json \
  desktop-extension/pyproject.toml uv.lock README.md CHANGELOG.md docs/INSTALL.md docs/V1_READINESS.md
git commit -m "chore: release vX.Y.Z"
```

## GitHub Release

Create and push a `vX.Y.Z` tag:

```bash
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

The `Release` workflow runs in five stages:

1. `build`: runs the quality gate, builds the wheel/source distribution and
   `albumentationsx-mcp-<version>.mcpb`, writes `SHA256SUMS`, and uploads Python and MCPB files as separate workflow
   artifacts.
2. `publish-pypi`: waits for the protected GitHub environment `pypi`, then publishes the same artifact to PyPI through
   Trusted Publishing. The MCPB is never published to PyPI.
3. `github-release`: uses the exact tag section extracted and validated from `CHANGELOG.md` during `build`, creates the
   GitHub Release with those notes, and attaches the Python package, MCPB, and checksum. A missing or empty version
   section fails before package publication instead of generating unrelated repository-wide notes.
4. `post-release-smoke`: checks PyPI's direct version JSON endpoint, then runs the published package with `uvx`.
5. `publish-mcp-registry`: publishes and verifies the MCP Registry metadata.

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

## Claude Desktop MCPB

The MCPB is a thin UV wrapper around the exact release version on PyPI. Source validation is owned by
`scripts/check_desktop_extension.py`; schema validation and packing are owned by the pinned official MCPB CLI through
`scripts.build_desktop_extension`. The release pipeline keeps this bundle in a separate workflow artifact so a wildcard
PyPI upload can never include it.

Before attaching the bundle, confirm that the build output contains only the five expected source files and verify the
published digest against `SHA256SUMS`. Users install the `.mcpb` from Claude Desktop's extension settings and select
explicit read and write directories; no home-directory default is shipped.

Each GitHub Release contains the versioned `albumentationsx-mcp-<version>.mcpb` and a byte-identical
`albumentationsx-mcp.mcpb` alias. Create the alias before generating `SHA256SUMS` so both names are verifiable. The
stable name powers the public `releases/latest/download/albumentationsx-mcp.mcpb` URL; retain the versioned name for
audits and reproducible support instructions.

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
uv run python scripts/check_published_package_smoke.py
```

Verify MCP Registry metadata:

```bash
uv run python scripts/check_mcp_registry_status.py
```

Export reviewable host acceptance evidence:

```bash
uv run python scripts/export_manual_host_acceptance_packet.py --output /tmp/albu-host-acceptance.md
uv run python scripts/record_host_manual_run.py --host Codex --status passed --date 2026-06-19 \
  --evidence "Codex app listed tools, read workflow resources, and ran run_host_smoke_check."
uv run python scripts/validate_host_manual_runs.py
uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md
uv run python scripts/check_host_acceptance_report.py
```

This artifact records automated release coverage and keeps manual host UI status pending until a reviewer adds dated
host-specific evidence to `docs/HOST_MANUAL_RUNS.json`. The record shape is documented in
`docs/HOST_MANUAL_RUNS.schema.json`.
The generated evidence freshness guard fails if this committed acceptance report is stale.

For a release that requires complete manual host UI evidence, run the strict gate after recording all host notes:

```bash
uv run python scripts/check_manual_host_acceptance.py
```
