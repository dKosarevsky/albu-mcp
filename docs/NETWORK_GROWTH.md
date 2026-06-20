# Network Growth Plan

This plan keeps public discovery work explicit, repeatable, and privacy-safe. It separates source-of-truth registry
publication from third-party directory visibility and community outreach.

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

Use GitHub Discussions or issues before opening a docs PR against AlbumentationsX. The first message should be short and
concrete:

Current status: upstream issue opened at
[albumentations-team/AlbumentationsX#285](https://github.com/albumentations-team/AlbumentationsX/issues/285).

```markdown
Hi, I built a small MCP server for AlbumentationsX workflows:
https://github.com/dKosarevsky/albu-mcp

It lets MCP hosts discover transforms, validate pipelines, render deterministic local preview batches, collect concrete
feedback such as `too_noisy:high`, compare preview runs, and export reproducible pipeline specs.

The target use case is interactive dataset augmentation review: an agent proposes several distorted variants, the user
rejects examples that are too noisy, and the accepted pipeline is exported for training/review.

Would this fit as a community integration link or example in the AlbumentationsX docs?
```

Avoid claiming official affiliation unless AlbumentationsX maintainers explicitly approve it.

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
