# v1.5 Real Sample Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a golden MCP eval that proves `run_host_smoke_check` can lead into a real `render_preview_batch` and `compare_preview_runs` workflow on deterministic sample images.

**Architecture:** Keep sample image generation inside `scripts/run_golden_evals.py` because it is verification data, not server runtime behavior. Add tests that lock the scenario declaration, runner path, and non-uniform sample image properties. Update docs and release notes after the workflow is green.

**Tech Stack:** Python 3.10+, FastMCP stdio client, Pillow, NumPy, PyYAML, pytest, ruff, ty, uv.

---

### Task 1: Golden Eval Contract Tests

**Files:**
- Modify: `tests/test_golden_evals.py`
- Modify: `evals/golden_mcp_scenarios.yaml`
- Modify: `scripts/run_golden_evals.py`

- [ ] **Step 1: Write the failing scenario contract assertions**

Add `real_sample_scenario` lookup in `test_golden_eval_assets_are_present` and extend the expected scenario set:

```python
real_sample_scenario = next(
    scenario for scenario in scenarios["scenarios"] if scenario["name"] == "real_sample_preview_smoke"
)

assert {scenario["name"] for scenario in scenarios["scenarios"]} == {
    "client_smoke_resource_flow",
    "diagnostics_resource_flow",
    "classification_recommend_validate_explain_export",
    "preview_lifecycle",
    "preview_batch_compare",
    "preview_quality_tuning_summary",
    "real_sample_preview_smoke",
}
assert real_sample_scenario["real_sample_smoke"] is True
assert real_sample_scenario["input_count"] == 3
assert real_sample_scenario["compare_preview"] is True
assert "_run_real_sample_smoke" in runner_source
```

- [ ] **Step 2: Run the focused test to verify RED**

Run: `uv run pytest tests/test_golden_evals.py::test_golden_eval_assets_are_present -q`

Expected: FAIL because `real_sample_preview_smoke` is not declared or `_run_real_sample_smoke` is missing.

- [ ] **Step 3: Add the scenario and route flag**

Append this scenario to `evals/golden_mcp_scenarios.yaml`:

```yaml
  - name: real_sample_preview_smoke
    task: classification
    intensity: low
    targets: ["image"]
    export_format: json
    preview: false
    real_sample_smoke: true
    input_count: 3
    variants_per_image: 1
    seed: 271
    max_side: 160
    compare_preview: true
    assert_quality_summary: true
    feedback_tags: ["too_noisy:low"]
```

Add routing in `_run_scenario` before the generic recommendation lifecycle:

```python
if scenario.get("real_sample_smoke"):
    await _run_real_sample_smoke(session, scenario, images_dir)
```

- [ ] **Step 4: Run focused test to verify partial GREEN is blocked by missing helper**

Run: `uv run pytest tests/test_golden_evals.py::test_golden_eval_assets_are_present -q`

Expected: PASS once `_run_real_sample_smoke` symbol exists in source, or FAIL with that missing symbol until Task 2 adds it.

### Task 2: Deterministic Sample Image Helper

**Files:**
- Modify: `scripts/run_golden_evals.py`
- Modify: `tests/test_golden_evals.py`

- [ ] **Step 1: Write the failing helper test**

Add a focused unit test:

```python
def test_real_sample_smoke_inputs_are_non_uniform_rgb_images(tmp_path: Path) -> None:
    from scripts.run_golden_evals import _write_real_sample_inputs

    paths = _write_real_sample_inputs(tmp_path, {"name": "real_sample_preview_smoke", "input_count": 3})

    assert len(paths) == 3
    for path in paths:
        assert path.parent == tmp_path / "real-sample-preview-smoke"
        assert path.suffix == ".png"
        from PIL import Image
        import numpy as np

        image = Image.open(path)
        assert image.mode == "RGB"
        pixels = np.asarray(image)
        assert pixels.shape == (96, 128, 3)
        assert int(pixels.max()) > int(pixels.min())
        assert len({tuple(pixel) for row in pixels for pixel in row}) > 16
```

- [ ] **Step 2: Run the focused test to verify RED**

Run: `uv run pytest tests/test_golden_evals.py::test_real_sample_smoke_inputs_are_non_uniform_rgb_images -q`

Expected: FAIL because `_write_real_sample_inputs` does not exist.

- [ ] **Step 3: Implement deterministic image generation**

In `scripts/run_golden_evals.py`, import `ImageDraw` from Pillow and add:

```python
def _write_real_sample_inputs(images_dir: Path, scenario: dict[str, Any]) -> list[Path]:
    sample_dir = images_dir / str(scenario["name"]).replace("_", "-")
    sample_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index in range(int(scenario.get("input_count", 3))):
        image = _build_real_sample_image(index)
        image_path = sample_dir / f"sample-{index:02d}.png"
        image.save(image_path)
        paths.append(image_path)
    return paths


def _build_real_sample_image(index: int) -> Image.Image:
    width, height = 128, 96
    x = np.linspace(0, 1, width, dtype=np.float32)
    y = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    red = np.clip((x * 160) + 40 + index * 12, 0, 255)
    green = np.clip((y * 150) + 55 + index * 7, 0, 255)
    blue = np.clip(((1 - x) * 120) + (y * 80) + 30, 0, 255)
    image_array = np.dstack(
        [
            np.tile(red, (height, 1)),
            np.tile(green, (1, width)),
            blue,
        ],
    ).astype(np.uint8)
    image = Image.fromarray(image_array, mode="RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((18 + index * 8, 20, 72 + index * 8, 70), outline=(20, 45, 90), width=3)
    draw.ellipse((54, 28 + index * 4, 96, 70 + index * 4), outline=(170, 45, 45), width=3)
    draw.line((8, 86 - index * 5, 120, 78 - index * 3), fill=(245, 245, 245), width=2)
    return image
```

- [ ] **Step 4: Run the helper test to verify GREEN**

Run: `uv run pytest tests/test_golden_evals.py::test_real_sample_smoke_inputs_are_non_uniform_rgb_images -q`

Expected: PASS.

### Task 3: Real Sample Smoke Workflow

**Files:**
- Modify: `scripts/run_golden_evals.py`
- Modify: `tests/test_golden_evals.py`

- [ ] **Step 1: Write failing full-run expectation**

In `test_golden_eval_runner_executes_scenarios_over_stdio`, add:

```python
assert "real_sample_preview_smoke: ok" in completed.stdout
```

- [ ] **Step 2: Run the full golden test to verify RED**

Run: `uv run pytest tests/test_golden_evals.py::test_golden_eval_runner_executes_scenarios_over_stdio -q`

Expected: FAIL until `_run_real_sample_smoke` performs the complete render/compare/delete workflow.

- [ ] **Step 3: Implement `_run_real_sample_smoke`**

Add a helper that:

1. Calls `run_host_smoke_check`.
2. Asserts `status == "ok"` and `preview_ready is True`.
3. Copies `preview_request_template.request`.
4. Replaces `input_paths` with `_write_real_sample_inputs(...)`.
5. Sets `variants_per_image`, `seed`, and `max_side` from the scenario.
6. Calls `render_preview_batch`.
7. Reads the manifest with `get_preview_manifest`.
8. Asserts manifest input count, image artifact count, contact sheet count, and non-empty contact sheet files.
9. Calls `adjust_pipeline` with `feedback_tags`.
10. Renders a candidate preview on the same sample paths.
11. Calls `compare_preview_runs`.
12. Asserts `quality_summary.baseline.image_count` and `quality_summary.candidate.image_count` match the expected image count.
13. Deletes baseline and candidate runs.

- [ ] **Step 4: Run full golden test to verify GREEN**

Run: `uv run pytest tests/test_golden_evals.py -q`

Expected: PASS and stdout contains `real_sample_preview_smoke: ok`.

### Task 4: Documentation and Release Notes

**Files:**
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `docs/V1_READINESS.md`
- Modify: `CHANGELOG.md`
- Optionally modify: `pyproject.toml`, `server.json`, `uv.lock`, `docs/INSTALL.md`

- [ ] **Step 1: Document the workflow**

Mention that golden evals now include a real sample first-preview smoke using `run_host_smoke_check`, `render_preview_batch`, `get_preview_manifest`, `adjust_pipeline`, and `compare_preview_runs`.

- [ ] **Step 2: Add changelog entry**

Add under `Unreleased`:

```markdown
### Added
- Added a real sample preview golden smoke that verifies the host-smoke template can render and compare deterministic local image previews over MCP stdio.
```

- [ ] **Step 3: Decide release**

If publishing as `v1.5.0`, move the changelog entry under `## 1.5.0 - 2026-06-15`, bump package metadata, run `uv lock`, verify release version, create tag, push, and watch CI/release workflows.

### Task 5: Verification

**Files:**
- No code changes expected.

- [ ] **Step 1: Run focused verification**

Run:

```bash
uv run pytest tests/test_golden_evals.py -q
uv run python scripts/run_golden_evals.py
```

Expected: all scenarios pass and `real_sample_preview_smoke: ok` appears.

- [ ] **Step 2: Run full local gate**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv build
```

Expected: all commands exit 0.

- [ ] **Step 3: Commit and push**

Create separate commits for implementation, docs, and release metadata. Push `main` and any release tag.
