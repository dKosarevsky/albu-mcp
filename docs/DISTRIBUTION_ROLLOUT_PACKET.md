# Distribution Rollout Packet

Package: `albumentationsx-mcp==1.17.1`
Release tag: `vX.Y.Z-rc.1`
Distribution status: `blocked_until_rc_cutover`
Rollout status: `blocked_until_rc_distribution`
Public announcement allowed: `false`

## Announcement Policy

Announce only after RC tag, release, package, and visibility checks pass.

## Rollout Channels

| Channel | Status | URL | Check | Next Action |
| --- | --- | --- | --- | --- |
| PyPI | `blocked_until_rc_cutover` | https://pypi.org/project/albumentationsx-mcp/ | `uv run python scripts/check_published_package_smoke.py --version 1.15.0` | Verify PyPI package page after RC publication. |
| GitHub Release | `blocked_until_rc_cutover` | https://github.com/dKosarevsky/albu-mcp/releases | `gh release view vX.Y.Z-rc.1` | Verify GitHub Release after RC publication. |
| Official MCP Registry | `blocked_until_rc_cutover` | https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp | `uv run python scripts/check_mcp_registry_status.py` | Verify MCP Registry server page after RC publication. |
| AlbumentationsX upstream docs | `ready_after_rc` | https://github.com/albumentations-team/AlbumentationsX/blob/main/docs/integrations/mcp.md | `Manual link check after upstream docs rebuild.` | Verify AlbumentationsX upstream docs link after RC publication. |
| GitHub Feedback Intake | `ready` | https://github.com/dKosarevsky/albu-mcp/issues/new/choose | `Manual issue template smoke check.` | Route host, workflow, dataset health, and feature feedback through issue templates. |

## Post-RC Checks

- `uv run python scripts/check_published_package_smoke.py --version 1.15.0`
- `uv run python scripts/check_mcp_registry_status.py`
- `uv run python scripts/check_directory_presence.py`

## Announcement Sources

- `docs/LAUNCH_KIT.md`
- `docs/ADOPTION_PACKET.md`
- `docs/DEMO.md`
- `examples/distortion_review_workflow.md`

## Source Docs

- `docs/DISTRIBUTION_READINESS_PACK.md`
- `docs/NETWORK_GROWTH_TRACKER.md`
- `docs/V1_GROWTH_CUTOVER_REPORT.md`

## Next Actions

- Complete P0 host evidence and RC cutover before public rollout.
- Keep announcement copy prepared but unpublished.
- Regenerate this packet after RC distribution readiness changes.
