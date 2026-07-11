# V1 Release Train

Package: `albumentationsx-mcp==1.16.0`
Release allowed: `false`
Manual gate count: `6`

## Decision

Do not publish a stable v1 release until all manual host evidence gates pass.

## Pre-Release Steps

- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
- `uv run python scripts/export_v1_trust_gates.py --output docs/V1_TRUST_GATES.md`
- `uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md`
- `uv run python scripts/check_release_readiness.py`
- `uv run python scripts/run_golden_evals.py`
- `uv build`

## Publish Steps

- `git tag v<next-version>`
- `git push origin v<next-version>`
- `gh release create v<next-version> --verify-tag --notes-file CHANGELOG.md`
- `wait for GitHub release workflow and PyPI Trusted Publishing`
- `run MCP Registry publish workflow after PyPI is visible`

## Post-Release Steps

- `uvx --from albumentationsx-mcp==<next-version> albumentationsx-mcp --help`
- `uv run python scripts/check_mcp_registry_status.py`
- `uv run python scripts/check_directory_presence.py`
- `uv run python scripts/export_network_growth_tracker.py --output docs/NETWORK_GROWTH_TRACKER.md`
