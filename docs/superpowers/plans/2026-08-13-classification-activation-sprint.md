# Classification Robustness Activation Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect qualified discovery to three voluntary classification preview adjustment loops through one measurable,
privacy-safe 14-day campaign.

**Architecture:** Keep MCP runtime behavior unchanged. Put campaign analysis in a pure typed domain module, keep live
GitHub/PyPI access in script adapters, and treat generated documentation plus GitHub issue forms as delivery adapters.
Only aggregate public metadata and deliberately submitted feedback enter the report.

**Tech Stack:** Python 3.10-3.13, standard-library HTTP/JSON/date parsing, PyYAML, pytest fixtures and parametrization,
Ruff, ty, uv, GitHub Actions, MCPB release workflow.

---

### Task 1: Canonical Classification Use Case

**Files:**
- Create: `docs/use-cases/CLASSIFICATION_ROBUSTNESS.md`
- Modify: `README.md`
- Modify: `docs/INDEX.md`
- Create: `tests/test_classification_activation_docs.py`

- [ ] **Step 1: Write a failing documentation contract**

```python
def test_classification_use_case_is_a_complete_activation_path() -> None:
    guide = Path("docs/use-cases/CLASSIFICATION_ROBUSTNESS.md").read_text(encoding="utf-8")
    assert "run_host_smoke_check" in guide
    assert "run_first_preview" in guide
    assert "too_noisy:high" in guide
    assert "render -> reject -> adjust -> accept" in guide
    assert "workflow-feedback.yml" in guide
```

- [ ] **Step 2: Run `uv run pytest tests/test_classification_activation_docs.py -q`**

Expected: FAIL because the canonical use-case file does not exist.

- [ ] **Step 3: Add the concise executable guide and link it from README and the docs index**

The guide must include the existing comparison contact sheet, MCPB and `uvx` installation, one copyable host prompt,
bounded acceptance criteria, troubleshooting, the official Albumentations guide, and the voluntary feedback form.

- [ ] **Step 4: Run the focused test and README scaffolding test**

Run: `uv run pytest tests/test_classification_activation_docs.py tests/test_project_scaffolding.py -q`

Expected: PASS, with README still at or below 100 lines.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/INDEX.md docs/use-cases/CLASSIFICATION_ROBUSTNESS.md tests/test_classification_activation_docs.py
git commit -m "docs: add classification activation path"
```

### Task 2: Structured Voluntary Feedback Attribution

**Files:**
- Modify: `.github/ISSUE_TEMPLATE/workflow-feedback.yml`
- Modify: `docs/FIRST_PREVIEW_FEEDBACK.md`
- Modify: `tests/test_classification_activation_docs.py`

- [ ] **Step 1: Add a failing parameterized YAML contract**

```python
@pytest.mark.parametrize(
    ("field_id", "expected_option"),
    [
        ("campaign", "classification-robustness"),
        ("discovery_source", "albumentations-discord"),
        ("install_route", "claude-desktop-mcpb"),
        ("workflow_outcome", "accepted-after-adjustment"),
    ],
)
def test_workflow_feedback_collects_voluntary_activation_fields(field_id: str, expected_option: str) -> None:
    template = yaml.safe_load(Path(".github/ISSUE_TEMPLATE/workflow-feedback.yml").read_text())
    field = next(item for item in template["body"] if item.get("id") == field_id)
    assert expected_option in field["attributes"]["options"]
```

- [ ] **Step 2: Run the focused test and confirm it fails on the missing fields**

Run: `uv run pytest tests/test_classification_activation_docs.py -q`

Expected: FAIL with `StopIteration` for `campaign`.

- [ ] **Step 3: Add bounded dropdowns and document their privacy purpose**

Use stable slug values. Require `campaign` and `workflow_outcome`; offer `not-sure` for optional attribution dimensions.
Do not request email, organization, dataset identity, image content, or local paths.

- [ ] **Step 4: Run focused tests and Ruff**

Run: `uv run pytest tests/test_classification_activation_docs.py -q`

Run: `uv run ruff check tests/test_classification_activation_docs.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/ISSUE_TEMPLATE/workflow-feedback.yml docs/FIRST_PREVIEW_FEEDBACK.md tests/test_classification_activation_docs.py
git commit -m "feat: structure voluntary activation feedback"
```

### Task 3: Pure Campaign Activation Analysis

**Files:**
- Create: `src/albumentationsx_mcp/campaign_activation.py`
- Create: `tests/fixtures/campaign_activation_input.json`
- Create: `tests/test_campaign_activation.py`

- [ ] **Step 1: Write failing domain tests**

```python
def test_campaign_report_counts_only_completed_attributed_loops() -> None:
    report = build_campaign_activation_report(**_fixture())
    assert report["activation"]["completed_loops"] == 2
    assert report["activation"]["distinct_submitters"] == 2
    assert report["privacy"]["contains_issue_level_data"] is False

@pytest.mark.parametrize(
    ("as_of", "expected"),
    [("2026-08-20", "continue"), ("2026-08-28", "adjust")],
)
def test_campaign_report_applies_bounded_decision_policy(as_of: str, expected: str) -> None:
    payload = _fixture(as_of=as_of)
    assert build_campaign_activation_report(**payload)["recommendation"] == expected
```

- [ ] **Step 2: Run `uv run pytest tests/test_campaign_activation.py -q`**

Expected: FAIL because `albumentationsx_mcp.campaign_activation` does not exist.

- [ ] **Step 3: Implement validated pure aggregation and Markdown rendering**

Expose `build_campaign_activation_report(config, growth_report, workflow_feedback_issues)` and
`render_campaign_activation_markdown(report)`. Parse only stable issue-form headings, deduplicate submitters in memory,
and omit issue-level values from returned structures.

- [ ] **Step 4: Run focused tests, Ruff, formatting, and ty**

Run: `uv run pytest tests/test_campaign_activation.py -q`

Run: `uv run ruff check src/albumentationsx_mcp/campaign_activation.py tests/test_campaign_activation.py`

Run: `uv run ruff format --check src/albumentationsx_mcp/campaign_activation.py tests/test_campaign_activation.py`

Run: `uv run ty check`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/albumentationsx_mcp/campaign_activation.py tests/fixtures/campaign_activation_input.json tests/test_campaign_activation.py
git commit -m "feat: add privacy-safe activation analysis"
```

### Task 4: Reproducible Activation Report and Launch Pack

**Files:**
- Create: `scripts/export_campaign_activation_report.py`
- Modify: `scripts/export_growth_report.py`
- Modify: `scripts/export_launch_kit.py`
- Create: `docs/campaigns/classification-robustness-2026-08.json`
- Create: `docs/campaigns/CLASSIFICATION_ROBUSTNESS_LAUNCH.md`
- Modify: `docs/LAUNCH_KIT.md`
- Modify: `docs/GROWTH.md`
- Modify: `tests/test_campaign_activation.py`
- Modify: `tests/test_network_growth_tracker.py`

- [ ] **Step 1: Write failing offline CLI, pagination, and launch-copy tests**

```python
def test_activation_cli_supports_reproducible_offline_input(tmp_path: Path) -> None:
    output = tmp_path / "activation.json"
    subprocess.run(
        [sys.executable, "scripts/export_campaign_activation_report.py", "--input", str(FIXTURE_PATH),
         "--format", "json", "--output", str(output)],
        check=True,
    )
    report = json.loads(output.read_text())
    assert report["campaign"]["id"] == "classification-robustness"
```

- [ ] **Step 2: Run focused tests and confirm missing CLI/copy failures**

Run: `uv run pytest tests/test_campaign_activation.py tests/test_network_growth_tracker.py -q`

Expected: FAIL because the campaign CLI and focused launch pack do not exist.

- [ ] **Step 3: Implement live/offline adapters and deterministic launch copy**

Reuse the growth payload fetcher through a public adapter function. Fetch GitHub issues page by page with labels and
state filters. Generate Discord, X, and generic copy from the canonical destination; keep third-party publication
manual and store only real publication URLs/timestamps.

- [ ] **Step 4: Record the pre-publication baseline and regenerate generated docs**

Run:
`GH_TOKEN="$(gh auth token)" uv run python scripts/export_campaign_activation_report.py --config docs/campaigns/classification-robustness-2026-08.json --output /tmp/classification-activation-baseline.md`

Expected: aggregate report with zero completed loops and no issue-level data.

- [ ] **Step 5: Run focused tests and static checks**

Run: `uv run pytest tests/test_campaign_activation.py tests/test_growth_report.py tests/test_network_growth_tracker.py -q`

Run: `uv run ruff check src scripts tests`

Run: `uv run ruff format --check src scripts tests`

Run: `uv run ty check`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/export_campaign_activation_report.py scripts/export_growth_report.py scripts/export_launch_kit.py docs/campaigns docs/LAUNCH_KIT.md docs/GROWTH.md tests/test_campaign_activation.py tests/test_growth_report.py tests/test_network_growth_tracker.py
git commit -m "feat: add measurable activation campaign"
```

### Task 5: Patch Release and Public Campaign Baseline

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `.codex-plugin/plugin.json`
- Modify: `.mcp.json`
- Modify: `desktop-extension/manifest.json`
- Modify: `desktop-extension/pyproject.toml`
- Modify: `server.json`
- Modify: `mcp-app/package.json`
- Modify: `mcp-app/package-lock.json`
- Modify: `mcp-app/src/main.ts`
- Modify: `src/albumentationsx_mcp/ui/preview-review.html`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_server.py`
- Modify: `tests/test_desktop_extension_build.py`

- [ ] **Step 1: Add the patch release notes and update synchronized public versions to `1.21.1`**

Describe the canonical use case, voluntary attribution, and aggregate activation report. Update the exact package pins
in `.mcp.json` and `desktop-extension/pyproject.toml`, Registry metadata in `server.json`, plugin and desktop manifests,
and the MCP App package/runtime version. State explicitly that the MCP tool/resource/prompt surface is unchanged and
runtime telemetry remains disabled.

- [ ] **Step 2: Regenerate lock and generated reports**

Run: `uv lock`

Run: `npm --prefix mcp-app install`

Run: `npm --prefix mcp-app run build`

Run `uv run python scripts/check_release_readiness.py --tag v1.21.1`; if it reports a generated-document diff, execute
the exact exporter command printed by that check and rerun the guard. Historical `1.20.0 -> 1.21.0` evidence and its
tests remain unchanged because they describe an already observed release transition.

- [ ] **Step 3: Run the complete release gate**

Run: `uv run pytest`

Run: `uv run ruff check .`

Run: `uv run ruff format --check .`

Run: `uv run ty check`

Run: `uv run python scripts/check_release_readiness.py --tag v1.21.1`

Run: `uv build`

Run: `uv run python -m scripts.build_desktop_extension --output-dir dist/mcpb`

Expected: all commands PASS and both Python distributions plus the MCPB validate.

- [ ] **Step 4: Commit, review, push, merge, and tag**

```bash
git add -A
git commit -m "release: prepare v1.21.1 activation sprint"
git push -u origin codex/classification-activation-sprint
gh pr create --base main --head codex/classification-activation-sprint --title "Launch classification activation sprint"
```

Wait for required checks, merge the PR, create and push signed/annotated `v1.21.1`, then verify the GitHub release,
PyPI package, stable MCPB asset, and Registry entry before calling the campaign published.
