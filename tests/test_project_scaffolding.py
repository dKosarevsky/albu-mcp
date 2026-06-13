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
    assert Path("CHANGELOG.md").exists()
    assert Path("server.json").exists()
    assert Path("examples/claude_desktop_config.json").exists()
    assert Path("examples/claude_desktop_pypi_config.json").exists()
    assert Path("examples/cursor_mcp_config.json").exists()
    assert Path("examples/codex_mcp_config.toml").exists()
    assert Path("examples/classification_pipeline.json").exists()
    assert Path("scripts/render_demo_assets.py").exists()
    assert Path("docs/DEMO.md").exists()


def test_changelog_tracks_public_releases_and_next_features() -> None:
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "## 0.2.1" in changelog
    assert "## 0.2.0" in changelog
    assert "## 0.1.0" in changelog
    assert "demo" in changelog.lower()
    assert "mcp registry" in changelog.lower()
    assert "feedback severity" in changelog.lower()


def test_release_workflow_and_readme_publish_instructions_are_present() -> None:
    release_workflow = Path(".github/workflows/release.yml")
    readme = Path("README.md").read_text(encoding="utf-8")
    release_docs = Path("docs/RELEASE.md")

    assert release_workflow.exists()
    workflow = yaml.safe_load(release_workflow.read_text(encoding="utf-8"))
    build_commands = "\n".join(step.get("run", "") for step in workflow["jobs"]["build"]["steps"])
    release_commands = "\n".join(step.get("run", "") for step in workflow["jobs"]["github-release"]["steps"])
    assert "uv build" in build_commands
    assert "gh release create" in release_commands
    assert "uvx --from albumentationsx-mcp albumentationsx-mcp" in readme
    assert "uv publish --trusted-publishing automatic" in release_docs.read_text(encoding="utf-8")


def test_release_workflow_publishes_to_pypi_with_trusted_publishing() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/release.yml").read_text(encoding="utf-8"))
    publish_job = workflow["jobs"]["publish-pypi"]
    release_job = workflow["jobs"]["github-release"]
    publish_commands = "\n".join(step.get("run", "") for step in publish_job["steps"])

    assert publish_job["needs"] == "build"
    assert publish_job["environment"]["name"] == "pypi"
    assert publish_job["environment"]["url"] == "https://pypi.org/project/albumentationsx-mcp/"
    assert publish_job["permissions"]["id-token"] == "write"
    assert publish_job["permissions"]["contents"] == "read"
    assert "uv publish --trusted-publishing automatic dist/*" in publish_commands
    assert release_job["needs"] == "publish-pypi"
    assert release_job["permissions"]["contents"] == "write"


def test_public_package_metadata_is_polished() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "https://img.shields.io/pypi/v/albumentationsx-mcp" in readme
    assert "https://pypi.org/project/albumentationsx-mcp/" in readme
    assert "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp" in readme
    assert "[project.urls]" in pyproject
    assert '"Repository" = "https://github.com/dKosarevsky/albu-mcp"' in pyproject
    assert '"Documentation" = "https://github.com/dKosarevsky/albu-mcp/blob/main/docs/USAGE.md"' in pyproject
    assert (
        '"MCP Registry" = "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp"'
        in pyproject
    )
    assert '"Development Status :: 3 - Alpha"' in pyproject
    assert '"Framework :: Pytest"' in pyproject
    assert '"Topic :: Scientific/Engineering :: Artificial Intelligence"' in pyproject


def test_public_docs_describe_current_preview_workflow() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    server_json = json.loads(Path("server.json").read_text(encoding="utf-8"))

    assert "## What Changed In 0.2" in readme
    assert "batch previews" in readme
    assert "compare preview runs" in readme
    assert "agent workflow resources" in readme
    assert "batch previews" in server_json["description"]
    assert "compare preview runs" in server_json["description"]


def test_release_workflow_checks_versions_and_smokes_published_package() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/release.yml").read_text(encoding="utf-8"))
    build_commands = "\n".join(step.get("run", "") for step in workflow["jobs"]["build"]["steps"])
    smoke_job = workflow["jobs"]["post-release-smoke"]
    smoke_commands = "\n".join(step.get("run", "") for step in smoke_job["steps"])

    assert Path("scripts/check_release_version.py").exists()
    assert "uv run python scripts/check_release_version.py" in build_commands
    assert smoke_job["needs"] == "github-release"
    assert 'uvx --from "albumentationsx-mcp==${GITHUB_REF_NAME#v}" albumentationsx-mcp --help' in smoke_commands


def test_mcp_registry_metadata_is_ready_for_pypi_distribution() -> None:
    server_json = json.loads(Path("server.json").read_text(encoding="utf-8"))
    readme = Path("README.md").read_text(encoding="utf-8")

    assert server_json["name"] == "io.github.dKosarevsky/albu-mcp"
    assert len(server_json["description"]) <= 100
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
    assert "registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp" in commands
