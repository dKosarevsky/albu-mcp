import importlib
import subprocess
import sys
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
    assert all(item["date"] == "none" for item in report["manual_host_ui"])


def test_host_acceptance_markdown_reports_pending_manual_status() -> None:
    module = importlib.import_module("scripts.export_host_acceptance_report")
    report = module.build_host_acceptance_report(Path())

    markdown = module.dump_host_acceptance_markdown(report)

    assert "# Host Acceptance Evidence" in markdown
    assert "| Claude Desktop | pending | none | manual UI run not recorded |" in markdown
    assert "| MCP Registry metadata publish check | automated |" in markdown
    assert "Manual Host UI: pending" in markdown
    assert "Manual Host UI: passed" not in markdown


def test_host_acceptance_report_applies_dated_manual_run_records(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.export_host_acceptance_report")
    _write_minimal_release_metadata(tmp_path)
    manual_runs_path = tmp_path / "docs" / "HOST_MANUAL_RUNS.json"
    manual_runs_path.parent.mkdir()
    manual_runs_path.write_text(
        """
{
  "manual_host_ui": [
    {
      "host": "Codex",
      "status": "passed",
      "date": "2026-06-19",
      "evidence": "Codex app listed tools, read workflow resources, and ran run_host_smoke_check."
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    report = module.build_host_acceptance_report(tmp_path)
    markdown = module.dump_host_acceptance_markdown(report)
    codex = next(item for item in report["manual_host_ui"] if item["host"] == "Codex")
    cursor = next(item for item in report["manual_host_ui"] if item["host"] == "Cursor")

    assert report["summary"]["manual_host_ui"] == "partial"
    assert codex["status"] == "passed"
    assert codex["date"] == "2026-06-19"
    assert "run_host_smoke_check" in codex["evidence"]
    assert cursor["status"] == "pending"
    assert "| Codex | passed | 2026-06-19 | Codex app listed tools" in markdown
    assert "Manual Host UI: partial" in markdown


def test_host_acceptance_report_cli_runs_as_script(tmp_path: Path) -> None:
    output_path = tmp_path / "HOST_ACCEPTANCE_EVIDENCE.md"

    subprocess.run(  # noqa: S603 - regression test for direct script execution with a static command.
        [
            sys.executable,
            "scripts/export_host_acceptance_report.py",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Manual Host UI: pending" in output_path.read_text(encoding="utf-8")


def _write_minimal_release_metadata(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        """
[project]
name = "albumentationsx-mcp"
version = "9.9.9"
""".strip(),
        encoding="utf-8",
    )
    (root / "server.json").write_text(
        """
{
  "name": "io.github.dKosarevsky/albu-mcp",
  "version": "9.9.9",
  "packages": [
    {
      "registryType": "pypi",
      "identifier": "albumentationsx-mcp",
      "version": "9.9.9"
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
