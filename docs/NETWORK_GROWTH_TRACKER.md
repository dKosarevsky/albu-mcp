# Network Growth Tracker

Package: `albumentationsx-mcp==1.16.0`
Ready for v1: `false`

## Channels

| Channel | Status | URL | Next Action |
| --- | --- | --- | --- |
| PyPI | `published` | https://pypi.org/project/albumentationsx-mcp/ | Keep package metadata aligned with README and server.json before every release. |
| Official MCP Registry | `listed` | https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp | Run scripts/check_mcp_registry_status.py after publishing a new package version. |
| Glama | `listed` | https://glama.ai/mcp/servers/dKosarevsky/albu-mcp | Check title, categories, install command, and computer-vision wording after releases. |
| AlbumentationsX Docs | `merged` | https://github.com/albumentations-team/AlbumentationsX/pull/289 | Keep local onboarding and first-10-minutes docs aligned with the upstream guide. |
| GitHub Feedback Intake | `ready` | https://github.com/dKosarevsky/albu-mcp/issues/new/choose | Route host, workflow, dataset health, and feature feedback through issue templates. |

## Proof Assets

- `docs/HOST_PROOF_SPRINT_CHECKLIST.md`
- `docs/V1_LAUNCH_REPORT.md`
- `docs/HOST_ACCEPTANCE_EVIDENCE.md`

## Launch Assets

- `docs/LAUNCH_KIT.md`
- `docs/ADOPTION_PACKET.md`
- `docs/PUBLIC_ADOPTION_LOOP.md`
- `docs/DEMO.md`
- `examples/distortion_review_workflow.md`

## Feedback Templates

- `.github/ISSUE_TEMPLATE/host-acceptance.yml`
- `.github/ISSUE_TEMPLATE/workflow-feedback.yml`
- `.github/ISSUE_TEMPLATE/dataset-health.yml`
- `.github/ISSUE_TEMPLATE/feature-request.yml`

## Next Checks

- `uv run python scripts/check_directory_presence.py`
- `uv run python scripts/check_mcp_registry_status.py`
- `uv run python scripts/export_public_adoption_loop.py --output docs/PUBLIC_ADOPTION_LOOP.md`
- `uv run python scripts/export_network_growth_tracker.py --output docs/NETWORK_GROWTH_TRACKER.md`
