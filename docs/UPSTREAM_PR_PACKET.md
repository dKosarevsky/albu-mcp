# AlbumentationsX Upstream PR Packet

This packet records the upstream documentation contribution that became
[albumentations-team/AlbumentationsX#289](https://github.com/albumentations-team/AlbumentationsX/pull/289), now merged
into the AlbumentationsX docs at
[docs/integrations/mcp.md](https://github.com/albumentations-team/AlbumentationsX/blob/main/docs/integrations/mcp.md).
It remains useful as local wording guidance for future ecosystem docs and release notes.

AlbumentationsX MCP is not an official AlbumentationsX project. Keep that wording in any upstream PR unless
AlbumentationsX maintainers explicitly ask for different language.

## Upstream Placement

- Integrated upstream docs page:
  `https://github.com/albumentations-team/AlbumentationsX/blob/main/docs/integrations/mcp.md`.
- Short README pointer to the integration page.
- Local project references from README, install docs, and network-growth docs.

Avoid adding install instructions that imply official support or maintainer ownership.

## Accepted Upstream Snippet

```markdown
### Community integration: AlbumentationsX MCP

[AlbumentationsX MCP](https://github.com/dKosarevsky/albu-mcp) is a community Model Context Protocol server for
interactive AlbumentationsX augmentation workflows. It lets MCP hosts discover transforms, validate pipelines, render
deterministic local preview batches, collect concrete feedback such as `too_noisy:high`, compare preview runs, and
export reproducible pipeline specs. It also includes segmentation mask onboarding for COCO polygon/RLE masks and
YOLO-seg labels, so teams can inspect mask overlays before accepting geometric augmentation changes.

This is not an official AlbumentationsX project. It is useful when a team wants an assistant-guided review loop for
dataset augmentation robustness before exporting the final pipeline.
```

## PR Checklist Reference

- Link to the repository: `https://github.com/dKosarevsky/albu-mcp`.
- Link to the upstream request: `https://github.com/albumentations-team/AlbumentationsX/issues/285`.
- Link to the merged PR: `https://github.com/albumentations-team/AlbumentationsX/pull/289`.
- Use "community integration" wording.
- Include "not an official AlbumentationsX project".
- Do not ask users to upload private datasets or raw production images.
- Keep the example focused on local preview review, segmentation mask onboarding, structured feedback, and reproducible
  export.

## Validation Before Future Upstream Updates

Run the local project checks that keep the public MCP surface accurate before opening follow-up upstream docs changes:

```bash
uv run python scripts/check_release_readiness.py --tag v1.15.0 --format json
uv run python scripts/check_directory_presence.py --format json
uv run python scripts/run_golden_evals.py
```

Then re-check the current upstream docs and avoid wording that implies official ownership unless maintainers explicitly
ask for it.
