# Demo Workflow

This demo shows the public feedback loop that AlbumentationsX MCP is built for:

1. recommend a conservative baseline pipeline;
2. render deterministic batch previews;
3. collect structured feedback such as `too_noisy`;
4. render an adjusted candidate;
5. compare preview runs;
6. export the accepted pipeline.

Generate local demo assets with:

```bash
uv run python scripts/render_demo_assets.py --output-dir docs/assets/demo
```

The script writes a synthetic input image, a baseline contact sheet, a comparison contact sheet, `demo_report.md`, and a
manifest that names the MCP tools used in the workflow. Open `docs/assets/demo/demo_report.md` first: it is the
30-second visual review artifact for the generated baseline and candidate.

Committed demo assets live in `docs/assets/demo/`. Check that they match the generator with:

```bash
uv run python scripts/check_demo_assets.py --output-dir docs/assets/demo --check
```

The generated files are intentionally small and deterministic so they can be refreshed whenever README or usage examples
need screenshots.
