from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "albumentationsx-mcp"


def test_skills_sh_package_has_installable_agent_skill() -> None:
    skill_path = SKILL_DIR / "SKILL.md"
    skill = skill_path.read_text(encoding="utf-8")
    assert skill.startswith("---\n")

    _, frontmatter, body = skill.split("---", maxsplit=2)
    metadata = yaml.safe_load(frontmatter)

    assert metadata == {
        "name": "albumentationsx-mcp",
        "description": metadata["description"],
    }
    assert metadata["description"].startswith("Use when")
    assert len(metadata["description"]) <= 1024

    expected = [
        "uvx --from albumentationsx-mcp albumentationsx-mcp",
        "--allowed-root",
        "--artifact-root",
        "albumentationsx://examples/client-smoke",
        "run_host_smoke_check",
        "plan_dataset_onboarding",
        "build_review_packet",
        "validate_preview_request",
        "render_preview_batch",
        "record_preview_feedback",
        "adjust_pipeline",
        "export_pipeline",
        "diagnose_environment",
        "albumentationsx://diagnostics/guide",
        "albu-mcp activation real-adoption-cycle",
        "albu-mcp activation product-fix-closure-pipeline",
        "albu-mcp evidence import-wizard",
    ]
    for expected_text in expected:
        assert expected_text in body

    assert len(body.split()) <= 450
    assert not (SKILL_DIR / "README.md").exists()


def test_skills_sh_display_config_groups_agent_skill() -> None:
    config = json.loads((ROOT / "skills.sh.json").read_text(encoding="utf-8"))

    assert config["$schema"] == "https://skills.sh/schemas/skills.sh.schema.json"
    assert config["notGrouped"] == "bottom"
    assert config["groupings"] == [
        {
            "title": "AlbumentationsX MCP",
            "description": "Agent playbook for installing, configuring, and safely using AlbumentationsX MCP.",
            "skills": ["albumentationsx-mcp"],
        }
    ]


def test_readme_links_skills_sh_install_path() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    expected = [
        "[![skills.sh](https://skills.sh/b/dKosarevsky/albu-mcp)](https://skills.sh/dKosarevsky/albu-mcp)",
        "npx skills add dKosarevsky/albu-mcp",
        "installs agent guidance, not the MCP server",
        "uvx --from albumentationsx-mcp albumentationsx-mcp",
    ]
    for expected_text in expected:
        assert expected_text in readme


def test_skills_cli_local_install_artifacts_are_ignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".agents/" in gitignore
    assert "skills-lock.json" in gitignore
