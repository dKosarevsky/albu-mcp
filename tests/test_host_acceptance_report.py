import importlib
from pathlib import Path


def test_host_acceptance_report_keeps_manual_hosts_pending_by_default() -> None:
    module = importlib.import_module("scripts.export_host_acceptance_report")

    report = module.build_host_acceptance_report(Path())

    assert report["project"] == "albumentationsx-mcp"
    assert report["registry_name"] == "io.github.dKosarevsky/albu-mcp"
    assert report["version"] == report["server_json_version"]
    assert report["version"] == report["package_version"]
    assert report["pypi_package"] == "albumentationsx-mcp"
    assert {item["name"] for item in report["automated_coverage"]} >= {
        "pytest",
        "golden stdio evals",
        "output contract snapshots",
        "release build",
        "PyPI publish check",
        "MCP Registry metadata publish check",
    }
    assert {item["host"] for item in report["manual_host_ui"]} == {
        "Claude Desktop",
        "Claude Code",
        "Cursor",
        "Codex",
    }
    assert {item["status"] for item in report["manual_host_ui"]} == {"pending"}
    assert all("manual UI run not recorded" in item["evidence"] for item in report["manual_host_ui"])


def test_host_acceptance_markdown_reports_pending_manual_status() -> None:
    module = importlib.import_module("scripts.export_host_acceptance_report")
    report = module.build_host_acceptance_report(Path())

    markdown = module.dump_host_acceptance_markdown(report)

    assert "# Host Acceptance Evidence" in markdown
    assert "| Claude Desktop | pending | manual UI run not recorded |" in markdown
    assert "| MCP Registry metadata publish check | automated |" in markdown
    assert "Manual Host UI: pending" in markdown
    assert "Manual Host UI: passed" not in markdown
