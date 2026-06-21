# AlbumentationsX Upstream PR Packet

This packet is a ready-to-copy draft for a future AlbumentationsX documentation PR if the maintainers accept the
community integration request in
[albumentations-team/AlbumentationsX#285](https://github.com/albumentations-team/AlbumentationsX/issues/285).

AlbumentationsX MCP is not an official AlbumentationsX project. Keep that wording in any upstream PR unless
AlbumentationsX maintainers explicitly ask for different language.

## Suggested Placement

- A community integrations page.
- A short entry in an examples or ecosystem section.
- A link from augmentation workflow docs where interactive preview review is relevant.

Avoid adding install instructions that imply official support or maintainer ownership.

## Suggested upstream snippet

```markdown
### Community integration: AlbumentationsX MCP

[AlbumentationsX MCP](https://github.com/dKosarevsky/albu-mcp) is a community Model Context Protocol server for
interactive AlbumentationsX augmentation workflows. It lets MCP hosts discover transforms, validate pipelines, render
deterministic local preview batches, collect concrete feedback such as `too_noisy:high`, compare preview runs, and
export reproducible pipeline specs.

This is not an official AlbumentationsX project. It is useful when a team wants an assistant-guided review loop for
dataset augmentation robustness before exporting the final pipeline.
```

## PR Checklist

- Link to the repository: `https://github.com/dKosarevsky/albu-mcp`.
- Link to the upstream request: `https://github.com/albumentations-team/AlbumentationsX/issues/285`.
- Use "community integration" wording.
- Include "not an official AlbumentationsX project".
- Do not ask users to upload private datasets or raw production images.
- Keep the example focused on local preview review, structured feedback, and reproducible export.

## Validation Before Opening A PR

Run the local project checks that keep the public MCP surface accurate:

```bash
uv run python scripts/check_release_readiness.py --tag v1.11.0 --format json
uv run python scripts/check_directory_presence.py --format json
uv run python scripts/run_golden_evals.py
```

Then re-check the upstream issue. If maintainers decline the integration, keep this packet as a local outreach artifact
and do not open the upstream PR.
