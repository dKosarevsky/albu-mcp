# Network Growth Plan

This plan keeps public discovery work explicit, repeatable, and privacy-safe. It separates source-of-truth registry
publication from third-party directory visibility and community outreach.

The generated channel tracker is [docs/NETWORK_GROWTH_TRACKER.md](NETWORK_GROWTH_TRACKER.md). Regenerate it after
release or directory changes:

```bash
uv run python scripts/export_network_growth_tracker.py --output docs/NETWORK_GROWTH_TRACKER.md
```

## Current Directory Status

- Official MCP Registry: listed as active/latest for exact server search `io.github.dKosarevsky/albu-mcp`.
- Glama: listed as `AlbumentationsX MCP` under `dKosarevsky/albu-mcp`.

Check directory visibility with:

```bash
uv run python scripts/check_directory_presence.py
```

Use JSON output when another tool needs a structured result:

```bash
uv run python scripts/check_directory_presence.py --format json
```

Use a required-source guard for manual release or outreach checkpoints:

```bash
uv run python scripts/check_directory_presence.py --require-source glama
uv run python scripts/check_directory_presence.py --require-source official_registry
```

Keep live directory checks out of routine CI because third-party directories and search indexes can lag or rate-limit.
The release-critical MCP Registry guard remains `scripts/check_mcp_registry_status.py`.

## Official MCP Registry

Goal: keep `io.github.dKosarevsky/albu-mcp` discoverable through the source-of-truth registry API.

1. Publish or repair metadata only after the PyPI package is available.
2. Run `mcp-publisher publish` through the release workflow or the manual registry workflow.
3. Verify with `uv run python scripts/check_mcp_registry_status.py`.
4. Re-run `uv run python scripts/check_directory_presence.py --require-source official_registry`.
5. Keep the README badge at `active` only while `check_mcp_registry_status.py` confirms active/latest metadata.

## Glama

Goal: keep the independent directory card accurate and useful for computer-vision users.

Current listing signals to preserve:

- title: `AlbumentationsX MCP`;
- author/repository: `dKosarevsky/albu-mcp`;
- categories: image/video processing and AI/ML;
- description centered on transform discovery, validation, deterministic previews, and reproducible exports.

After user-visible releases, check the card and confirm that the package version, description, categories, and install
instructions still match the repository.

## Upstream Outreach

Status: MERGED.

- Upstream PR: [albumentations-team/AlbumentationsX#289](https://github.com/albumentations-team/AlbumentationsX/pull/289)
- Upstream docs source:
  [AlbumentationsX docs/integrations/mcp.md](https://github.com/albumentations-team/AlbumentationsX/blob/main/docs/integrations/mcp.md)
- Local source packet: [docs/UPSTREAM_PR_PACKET.md](UPSTREAM_PR_PACKET.md)

Next follow-up: keep local onboarding, first-10-minutes, and host proof docs aligned with the upstream guide. Avoid
claiming official ownership; describe this project as a community MCP integration accepted into the AlbumentationsX docs.

## Content Loop

The most useful public demo is not a broad feature list. Use one concrete loop:

1. Start from a small local image folder under `--allowed-root`.
2. Ask an MCP host for robustness-oriented distortions.
3. Reject one preview as too noisy.
4. Compare the adjusted preview run.
5. Export the accepted pipeline and report.

Reuse [docs/DEMO.md](DEMO.md) and [examples/distortion_review_workflow.md](../examples/distortion_review_workflow.md)
as the source material for screenshots, posts, and directory descriptions.

## Feedback Intake

Route public feedback by type:

- install or host compatibility reports: GitHub issue template `host-acceptance.yml`;
- augmentation workflow gaps: GitHub issue template `workflow-feedback.yml`;
- feature proposals: GitHub issue template `feature-request.yml`;
- general questions and early user stories: GitHub Discussions.

Do not ask users to upload private datasets or raw production images. Prefer descriptions, redacted paths, generated
demo images, and contact sheets that do not expose sensitive data.
