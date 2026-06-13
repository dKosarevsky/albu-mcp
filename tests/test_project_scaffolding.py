import json
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
    assert "uv run python scripts/run_golden_evals.py" in commands
    assert "ClientSession" in commands


def test_ci_workflow_uses_node24_ready_actions() -> None:
    workflow_path = Path(".github/workflows/ci.yml")
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["test"]["steps"]
    actions = {step["name"]: step["uses"] for step in steps if "uses" in step}
    setup_uv = next(step for step in steps if step.get("name") == "Install uv")

    assert actions["Check out repository"] == "actions/checkout@v5"
    assert actions["Install uv"] == "astral-sh/setup-uv@v7"
    assert actions["Set up Python"] == "actions/setup-python@v6"
    assert setup_uv["with"]["enable-cache"] is False


def test_usage_docs_and_examples_are_present() -> None:
    assert Path("docs/USAGE.md").exists()
    assert Path("docs/RELEASE.md").exists()
    assert Path("server.json").exists()
    assert Path("examples/claude_desktop_config.json").exists()
    assert Path("examples/classification_pipeline.json").exists()


def test_release_workflow_and_readme_publish_instructions_are_present() -> None:
    release_workflow = Path(".github/workflows/release.yml")
    readme = Path("README.md").read_text(encoding="utf-8")
    release_docs = Path("docs/RELEASE.md")

    assert release_workflow.exists()
    workflow = yaml.safe_load(release_workflow.read_text(encoding="utf-8"))
    commands = "\n".join(step.get("run", "") for step in workflow["jobs"]["release"]["steps"])
    assert "uv build" in commands
    assert "gh release create" in commands
    assert "uvx --from albumentationsx-mcp albumentationsx-mcp" in readme
    assert "uv publish --trusted-publishing automatic" in release_docs.read_text(encoding="utf-8")


def test_mcp_registry_metadata_is_ready_for_pypi_distribution() -> None:
    server_json = json.loads(Path("server.json").read_text(encoding="utf-8"))
    readme = Path("README.md").read_text(encoding="utf-8")

    assert server_json["name"] == "io.github.dKosarevsky/albu-mcp"
    assert server_json["packages"][0]["registryType"] == "pypi"
    assert server_json["packages"][0]["identifier"] == "albumentationsx-mcp"
    assert server_json["packages"][0]["transport"]["type"] == "stdio"
    assert "<!-- mcp-name: io.github.dKosarevsky/albu-mcp -->" in readme


def test_mcp_registry_publish_workflow_is_present() -> None:
    workflow_path = Path(".github/workflows/publish-mcp.yml")
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["publish"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)

    assert workflow["jobs"]["publish"]["permissions"]["id-token"] == "write"
    assert "mcp-publisher login github-oidc" in commands
    assert "mcp-publisher publish" in commands
