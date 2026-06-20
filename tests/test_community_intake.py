from pathlib import Path

import yaml


def test_github_issue_templates_collect_actionable_mcp_feedback() -> None:
    templates_dir = Path(".github/ISSUE_TEMPLATE")
    host_template = yaml.safe_load((templates_dir / "host-acceptance.yml").read_text(encoding="utf-8"))
    workflow_template = yaml.safe_load((templates_dir / "workflow-feedback.yml").read_text(encoding="utf-8"))
    feature_template = yaml.safe_load((templates_dir / "feature-request.yml").read_text(encoding="utf-8"))
    config = yaml.safe_load((templates_dir / "config.yml").read_text(encoding="utf-8"))

    assert host_template["name"] == "MCP host acceptance report"
    assert "host-acceptance" in host_template["labels"]
    assert "albumentationsx-mcp" in _template_text(host_template)
    assert "export_manual_host_acceptance_packet.py" in _template_text(host_template)
    for host in ["Claude Desktop", "Claude Code", "Cursor", "Codex"]:
        assert host in _template_text(host_template)

    assert workflow_template["name"] == "Preview workflow feedback"
    assert "workflow-feedback" in workflow_template["labels"]
    assert "too_noisy" in _template_text(workflow_template)
    assert "compare_preview_runs" in _template_text(workflow_template)
    assert "export_preview_report" in _template_text(workflow_template)

    assert feature_template["name"] == "Feature request"
    assert "enhancement" in feature_template["labels"]
    assert "MCP host" in _template_text(feature_template)

    assert config["blank_issues_enabled"] is True
    assert any(link["name"] == "Install and host setup docs" for link in config["contact_links"])


def test_community_feedback_guide_is_linked_and_privacy_safe() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    guide = Path("docs/COMMUNITY_FEEDBACK.md").read_text(encoding="utf-8")

    assert "[docs/COMMUNITY_FEEDBACK.md](docs/COMMUNITY_FEEDBACK.md)" in readme
    assert "host-acceptance.yml" in guide
    assert "workflow-feedback.yml" in guide
    assert "feature-request.yml" in guide
    assert "Do not upload private datasets" in guide
    assert "export_manual_host_acceptance_packet.py" in guide
    assert "albumentationsx://examples/distortion-review" in guide


def _template_text(template: object) -> str:
    return str(template)
