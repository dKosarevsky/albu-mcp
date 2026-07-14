# Network Growth Plan

This plan keeps public discovery work explicit, repeatable, and privacy-safe. It separates source-of-truth registry
publication from third-party directory visibility and community outreach.

The generated channel tracker is [docs/NETWORK_GROWTH_TRACKER.md](NETWORK_GROWTH_TRACKER.md). The product feedback loop
is [docs/PUBLIC_ADOPTION_LOOP.md](PUBLIC_ADOPTION_LOOP.md). Regenerate these after release or directory changes:

```bash
uv run python scripts/export_network_growth_tracker.py --output docs/NETWORK_GROWTH_TRACKER.md
uv run python scripts/export_public_adoption_loop.py --output docs/PUBLIC_ADOPTION_LOOP.md
```

Generate the aggregate demand and conversion report before and after a campaign:

```bash
GH_TOKEN="$(gh auth token)" uv run python scripts/export_growth_report.py --output /tmp/albu-growth.md
```

## Campaign Measurement

The audience-specific copy, prompt, destination, artifact, and success signal are generated in
[docs/LAUNCH_KIT.md](LAUNCH_KIT.md). The current campaign IDs are `classification-robustness`,
`detection-bbox-safety`, and `segmentation-mask-safety`.

Run one campaign at a time:

1. Capture the aggregate report before publication.
2. Select one campaign and one relevant discussion where its problem is already on topic.
3. Verify that the referenced artifact is synthetic, redacted, or safe to publish.
4. Publish manually from an account whose owner has approved the message.
5. Keep the prompt, destination URL, and success signal unchanged for seven days.
6. Capture the report again and record any voluntary workflow feedback separately.
7. Continue, revise, or stop based on qualified reach and the stated success signal, not raw downloads alone.

UTM parameters identify the prepared campaign in destination analytics where those analytics are available. GitHub
Traffic can still aggregate or omit referrer detail, so a campaign must not claim attribution that the available data
does not prove. GitHub views and top-10 referrers use a rolling 14-day window, so reports captured seven days apart
overlap; use those changes directionally. Preparation may be automated; third-party publication and community
interaction remain manual.

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
