# Distribution Readiness Pack

Package: `albumentationsx-mcp==1.18.0`
Release tag: `vX.Y.Z-rc.1`
Distribution status: `blocked_until_rc_cutover`
RC cutover allowed: `false`

## Publish Commands

- none

## Blocked Publish Commands

- `git tag vX.Y.Z-rc.1`
- `git push origin vX.Y.Z-rc.1`
- `gh release create vX.Y.Z-rc.1 --prerelease --generate-notes`

## Post-RC Checks

- `uv run python scripts/check_published_package_smoke.py --version 1.15.0`
- `uv run python scripts/check_mcp_registry_status.py`
- `uv run python scripts/check_directory_presence.py`

## Visibility Targets

| Target | URL | Check |
| --- | --- | --- |
| PyPI package page | https://pypi.org/project/albumentationsx-mcp/ | `uv run python scripts/check_published_package_smoke.py --version 1.15.0` |
| GitHub Release | https://github.com/dKosarevsky/albu-mcp/releases | `gh release view vX.Y.Z-rc.1` |
| MCP Registry server page | https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp | `uv run python scripts/check_mcp_registry_status.py` |
| AlbumentationsX upstream docs link | https://github.com/albumentations-team/AlbumentationsX/blob/main/docs/integrations/mcp.md | `Manual link check after upstream docs rebuild.` |

## Source Docs

- `docs/RELEASE.md`
- `docs/V1_RC_CUTOVER_GATE.md`
- `docs/NETWORK_GROWTH.md`
- `docs/UPSTREAM_PR_PACKET.md`

## Next Actions

- Keep distribution blocked until the hard RC cutover gate opens.
- Do not publish GitHub Release, PyPI package, or registry announcements before P0 evidence passes.
- Use this pack as the post-RC checklist once real-host evidence is recorded.
