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
        "albu-mcp evidence execution-pack --date YYYY-MM-DD",
        "albu-mcp evidence execution-pack-audit --input-dir evidence-session",
        "albu-mcp evidence execution-pack-progress --input-dir evidence-session",
        (
            "albu-mcp evidence execution-pack-status --input-dir evidence-session --format markdown "
            "--output evidence-session/status.md"
        ),
        "albu-mcp evidence preflight",
        "albu-mcp evidence import-wizard",
    ]
    for expected_text in expected:
        assert expected_text in body

    assert len(body.split()) <= 450
    assert not (SKILL_DIR / "README.md").exists()


def test_agent_skill_contains_first_run_playbook() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    expected = [
        "## First Run Prompt",
        "Use AlbumentationsX MCP on image or directory `DATASET_PATH`.",
        "`ALLOWED_ROOT`",
        "`ARTIFACT_ROOT`",
        "If `preview_ready` is false, call `diagnose_environment` and stop before rendering.",
        "Render at most 6 images on the first pass.",
        "Show the contact sheet path and ask for concrete feedback before `adjust_pipeline` or `export_pipeline`.",
    ]
    for expected_text in expected:
        assert expected_text in skill


def test_agent_skill_uses_client_smoke_tool_fallback() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "resource reads" in skill
    assert "resource reads are unavailable" in skill
    assert "`get_workflow_example`" in skill
    assert '`example_id="client-smoke"`' in skill
    assert "otherwise call `run_host_smoke_check` directly" not in skill
    assert "continue only when `preview_ready` is true" in skill


def test_agent_skill_documents_host_config_hints_and_stop_conditions() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    openai_yaml = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")

    expected_skill_text = [
        "## Host Config Hints",
        (
            "Codex plugin mode uses `.codex-plugin/plugin.json` and `.mcp.json`; "
            "its pinned server grants no user dataset root."
        ),
        "Set `ALBU_MCP_ALLOWED_ROOTS` and `ALBU_MCP_ARTIFACT_ROOT`, or use explicit absolute host args.",
        "stop unless `allowed_roots` contains the intended root and `preview_ready` is true.",
        "## Stop Conditions",
        "Missing real image or dataset-directory path: ask for one.",
        "Path outside `--allowed-root`: refuse that path and ask for a bounded path.",
        "User asks for many variants: render a small first batch before expanding.",
    ]
    for expected_text in expected_skill_text:
        assert expected_text in skill

    assert "exposure_too_weak" in skill

    assert "ask for dataset path, allowed root, and artifact root when they are missing" in openai_yaml


def test_agent_skill_guards_codex_plugin_preview_roots() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    expected = [
        "Codex plugin mode",
        "`.codex-plugin/plugin.json`",
        "`.mcp.json`",
        "`ALBU_MCP_ALLOWED_ROOTS`",
        "`ALBU_MCP_ARTIFACT_ROOT`",
        "grants no user dataset root",
        "stop unless `allowed_roots` contains the intended root",
    ]
    for expected_text in expected:
        assert expected_text in skill


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
