# v0.13 Install Guide Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a canonical host install guide and guard it with focused documentation tests before the next release.

**Architecture:** Keep runtime code unchanged. Add one `docs/INSTALL.md` onboarding artifact, route README and usage docs to
it, and add project-scaffolding assertions that keep the guide and host snippets aligned with the published PyPI command.

**Tech Stack:** Markdown docs, JSON/TOML host examples, `pytest`, `ruff`, `ty`, `uv`.

---

## File Structure

- Create: `docs/INSTALL.md`
  - Canonical host install guide for PyPI, local checkout, bounded filesystem roots, client snippets, smoke checks, and
    troubleshooting.
- Modify: `README.md`
  - Keep install section concise and link to `docs/INSTALL.md`; update v1-readiness wording.
- Modify: `docs/USAGE.md`
  - Point host configuration readers to the install guide before workflow details.
- Modify: `tests/test_project_scaffolding.py`
  - Add documentation contract checks for the guide and existing examples.
- Modify later in release task: `pyproject.toml`, `server.json`, `uv.lock`, `README.md`, `CHANGELOG.md`
  - Bump to `0.13.0` only after docs/tests are green.

## Task 1: Documentation Contract Test

**Files:**
- Modify: `tests/test_project_scaffolding.py`

- [ ] **Step 1: Add failing test**

Append this test near the other public docs tests:

```python
def test_install_guide_covers_host_setup_and_examples() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    usage = Path("docs/USAGE.md").read_text(encoding="utf-8")
    install = Path("docs/INSTALL.md").read_text(encoding="utf-8")
    claude_pypi = json.loads(Path("examples/claude_desktop_pypi_config.json").read_text(encoding="utf-8"))
    cursor = json.loads(Path("examples/cursor_mcp_config.json").read_text(encoding="utf-8"))
    codex = Path("examples/codex_mcp_config.toml").read_text(encoding="utf-8")

    required_terms = [
        "PyPI",
        "MCP Registry",
        "Claude Desktop",
        "Claude Code",
        "Cursor",
        "Codex",
        "--allowed-root",
        "--artifact-root",
        "Smoke Check",
        "Troubleshooting",
    ]

    assert "[docs/INSTALL.md](docs/INSTALL.md)" in readme
    assert "[INSTALL.md](INSTALL.md)" in usage
    for term in required_terms:
        assert term in install
    for config in [claude_pypi, cursor]:
        args = config["mcpServers"]["albumentationsx"]["args"]
        assert args[:3] == ["--from", "albumentationsx-mcp", "albumentationsx-mcp"]
        assert config["mcpServers"]["albumentationsx"]["command"] == "uvx"
    assert 'command = "uvx"' in codex
    assert 'args = ["--from", "albumentationsx-mcp", "albumentationsx-mcp"]' in codex
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
uv run pytest tests/test_project_scaffolding.py::test_install_guide_covers_host_setup_and_examples -q
```

Expected: fail because `docs/INSTALL.md` does not exist.

- [ ] **Step 3: Commit is not created yet**

Keep the failing test uncommitted until the guide passes it.

## Task 2: Canonical Install Guide

**Files:**
- Create: `docs/INSTALL.md`
- Modify: `README.md`
- Modify: `docs/USAGE.md`

- [ ] **Step 1: Create guide**

Add sections with these exact headings so the test has stable anchors:

```markdown
# Install AlbumentationsX MCP

## Recommended Path
## PyPI
## MCP Registry
## Bounded Local Access
## Claude Desktop
## Claude Code
## Cursor
## Codex
## Local Checkout
## Smoke Check
## Troubleshooting
## Safety Notes
```

Use `uvx --from albumentationsx-mcp albumentationsx-mcp` as the default command and show bounded variants with
`--allowed-root` and `--artifact-root`.

- [ ] **Step 2: Link from README and usage docs**

In `README.md`, link `docs/INSTALL.md` from the install section and v1-readiness paragraph. In `docs/USAGE.md`, link
`INSTALL.md` from `Host Configuration` before the JSON snippet.

- [ ] **Step 3: Run focused test**

Run:

```bash
uv run pytest tests/test_project_scaffolding.py::test_install_guide_covers_host_setup_and_examples -q
```

Expected: pass.

- [ ] **Step 4: Run docs-focused checks**

Run:

```bash
uv run pytest tests/test_project_scaffolding.py -q
uv run ruff check tests/test_project_scaffolding.py
uv run ty check tests/test_project_scaffolding.py
```

Expected: all pass.

- [ ] **Step 5: Commit docs and test**

Commit:

```bash
git add docs/INSTALL.md README.md docs/USAGE.md tests/test_project_scaffolding.py
git commit -m "docs: add mcp host install guide"
```

## Task 3: Release v0.13.0

**Files:**
- Modify: `pyproject.toml`
- Modify: `server.json`
- Modify: `uv.lock`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Bump version metadata**

Change project and registry versions from `0.12.0` to `0.13.0`. Add README release notes for install guide readiness and
move changelog entries from `Unreleased` to `0.13.0 - 2026-06-14`.

- [ ] **Step 2: Refresh lockfile**

Run:

```bash
uv lock
```

Expected: lockfile updates only package version metadata.

- [ ] **Step 3: Run full local verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv run python scripts/check_release_version.py v0.13.0
uv build
```

Expected: all pass.

- [ ] **Step 4: Commit release metadata**

Commit:

```bash
git add pyproject.toml server.json uv.lock README.md CHANGELOG.md
git commit -m "chore: release v0.13.0"
```

- [ ] **Step 5: Tag and push**

Run:

```bash
git tag v0.13.0
git push origin main
git push origin v0.13.0
```

Expected: GitHub CI and Release workflows start.

- [ ] **Step 6: Verify publication**

Watch CI/Release, dispatch MCP Registry publishing, then verify PyPI JSON, PyPI Simple, MCP Registry latest metadata, and
`uvx --from albumentationsx-mcp==0.13.0 albumentationsx-mcp --help`.
