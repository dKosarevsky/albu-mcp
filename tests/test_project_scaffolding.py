from pathlib import Path

import yaml


def test_readme_first_sentence_links_to_albumentationsx_repo() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert readme.startswith(
        "# AlbumentationsX MCP\n\n"
        "Model Context Protocol server for "
        "[AlbumentationsX](https://github.com/albumentations-team/AlbumentationsX)",
    )


def test_ci_workflow_runs_core_quality_gates() -> None:
    workflow_path = Path(".github/workflows/ci.yml")
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["test"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)

    assert workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"] == ["3.10", "3.11", "3.12", "3.13"]
    assert "uv run pytest" in commands
    assert "uv run ruff check ." in commands
    assert "uv run ruff format --check ." in commands
    assert "uv run ty check" in commands
    assert "uv build" in commands
    assert "ClientSession" in commands


def test_usage_docs_and_examples_are_present() -> None:
    assert Path("docs/USAGE.md").exists()
    assert Path("examples/claude_desktop_config.json").exists()
    assert Path("examples/classification_pipeline.json").exists()
