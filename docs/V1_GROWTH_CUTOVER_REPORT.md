# V1 Growth Cutover Report

Cutover status: `blocked_by_p0_evidence`
RC publish allowed: `false`
Automation status: `blocked`
Evidence status: `manual_evidence_required`
Beta campaign status: `ready_to_invite`
Growth status: `ready`

## Blocking Gates

- `p0_host_evidence`

## Growth Channels

| Channel | Status | URL | Next Action |
| --- | --- | --- | --- |
| PyPI | `published` | https://pypi.org/project/albumentationsx-mcp/ | Keep package metadata aligned with README and server.json before every release. |
| Official MCP Registry | `listed` | https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp | Run scripts/check_mcp_registry_status.py after publishing a new package version. |
| Glama | `listed` | https://glama.ai/mcp/servers/dKosarevsky/albu-mcp | Check title, categories, install command, and computer-vision wording after releases. |
| AlbumentationsX Docs | `merged` | https://github.com/albumentations-team/AlbumentationsX/pull/289 | Keep local onboarding and first-10-minutes docs aligned with the upstream guide. |
| GitHub Feedback Intake | `ready` | https://github.com/dKosarevsky/albu-mcp/issues/new/choose | Route host, workflow, dataset health, and feature feedback through issue templates. |

## Preflight Commands

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
- `uv run python scripts/check_release_readiness.py`
- `uv build`

## Publish Commands

- `git tag vX.Y.Z-rc.1`
- `git push origin vX.Y.Z-rc.1`
- `gh release create vX.Y.Z-rc.1 --prerelease --generate-notes`

## Next Cutover Actions

- Record real Codex and Claude Code P0 host evidence.
- Regenerate evidence, RC automation, and cutover reports.
- Run release readiness before creating an RC tag.
- Invite beta users with docs/BETA_CAMPAIGN_PACK.md while RC remains blocked.

## Source Docs

- `docs/V1_EVIDENCE_OPERATOR_PACKET.md`
- `docs/V1_RC_AUTOMATION_PACK.md`
- `docs/BETA_CAMPAIGN_PACK.md`
- `docs/NETWORK_GROWTH_TRACKER.md`
