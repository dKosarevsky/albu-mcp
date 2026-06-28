import importlib
import subprocess
import sys
from pathlib import Path


def test_host_acceptance_report_tracks_blocked_p0_hosts() -> None:
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
        "host acceptance evidence freshness",
    }
    assert {item["host"] for item in report["manual_host_ui"]} == {
        "Claude Desktop",
        "Claude Code",
        "Cursor",
        "Codex",
    }
    assert {item["status"] for item in report["manual_host_ui"]} == {"blocked", "pending"}
    assert {item["host"] for item in report["manual_host_ui"] if item["status"] == "blocked"} == {
        "Claude Code",
        "Codex",
    }
    assert {item["host"] for item in report["manual_host_ui"] if item["status"] == "pending"} == {
        "Claude Desktop",
        "Cursor",
    }
    assert {item["host"] for item in report["first_10_minutes_replay"]} == {
        "Claude Desktop",
        "Claude Code",
        "Cursor",
        "Codex",
    }
    assert {item["status"] for item in report["first_10_minutes_replay"]} == {"blocked", "pending"}


def test_host_acceptance_markdown_reports_pending_manual_status() -> None:
    module = importlib.import_module("scripts.export_host_acceptance_report")
    report = module.build_host_acceptance_report(Path())

    markdown = module.dump_host_acceptance_markdown(report)

    assert "# Host Acceptance Evidence" in markdown
    assert "| Claude Desktop | pending | none | manual UI run not recorded |" in markdown
    assert "| Codex | blocked | 2026-06-28 | Codex CLI host listed AlbumentationsX MCP resources/tools" in markdown
    assert "## First 10 Minutes Replay" in markdown
    assert "| Codex | blocked | 2026-06-28 | Codex CLI host run reached AlbumentationsX MCP discovery" in markdown
    assert "| MCP Registry metadata publish check | automated |" in markdown
    assert "| host acceptance evidence freshness | automated |" in markdown
    assert "Manual Host UI: blocked" in markdown
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
  ],
  "first_10_minutes_replay": [
    {
      "host": "Codex",
      "status": "passed",
      "date": "2026-06-22",
      "evidence": "Codex completed the first 10 minutes path.",
      "artifacts": ["docs/assets/demo/demo_report.md"]
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    report = module.build_host_acceptance_report(tmp_path)
    markdown = module.dump_host_acceptance_markdown(report)
    codex = next(item for item in report["manual_host_ui"] if item["host"] == "Codex")
    codex_replay = next(item for item in report["first_10_minutes_replay"] if item["host"] == "Codex")
    cursor = next(item for item in report["manual_host_ui"] if item["host"] == "Cursor")

    assert report["summary"]["manual_host_ui"] == "partial"
    assert report["summary"]["first_10_minutes_replay"] == "partial"
    assert codex["status"] == "passed"
    assert codex["date"] == "2026-06-19"
    assert "run_host_smoke_check" in codex["evidence"]
    assert codex_replay["status"] == "passed"
    assert codex_replay["artifacts"] == ["docs/assets/demo/demo_report.md"]
    assert cursor["status"] == "pending"
    assert "| Codex | passed | 2026-06-19 | Codex app listed tools" in markdown
    assert "| Codex | passed | 2026-06-22 | Codex completed the first 10 minutes path. |" in markdown
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

    assert "Manual Host UI: blocked" in output_path.read_text(encoding="utf-8")


def test_host_acceptance_report_freshness_check_rejects_stale_markdown(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.check_host_acceptance_report")
    _write_minimal_release_metadata(tmp_path)
    docs_path = tmp_path / "docs"
    docs_path.mkdir()
    _write_codex_manual_run(docs_path / "HOST_MANUAL_RUNS.json")
    report_path = docs_path / "HOST_ACCEPTANCE_EVIDENCE.md"
    report_path.write_text("# Host Acceptance Evidence\n\n- Manual Host UI: pending\n", encoding="utf-8")

    result = module.check_host_acceptance_report(root=tmp_path, report_path=report_path)

    assert result.ok is False
    assert result.expected_path == report_path
    assert "Host acceptance evidence is stale" in result.message
    assert "export_host_acceptance_report.py" in result.message
    assert "---" in result.diff
    assert "+++" in result.diff
    assert "Manual Host UI: pending" in result.diff
    assert "Manual Host UI: partial" in result.diff


def test_host_acceptance_report_freshness_check_cli_prints_stale_diff(tmp_path: Path) -> None:
    _write_minimal_release_metadata(tmp_path)
    docs_path = tmp_path / "docs"
    report_path = docs_path / "HOST_ACCEPTANCE_EVIDENCE.md"
    docs_path.mkdir()
    _write_codex_manual_run(docs_path / "HOST_MANUAL_RUNS.json")
    report_path.write_text("# Host Acceptance Evidence\n\n- Manual Host UI: pending\n", encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - regression test for direct script execution with controlled fixture paths.
        [
            sys.executable,
            "scripts/check_host_acceptance_report.py",
            "--root",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Host acceptance evidence is stale" in result.stderr
    assert "---" in result.stderr
    assert "+++" in result.stderr
    assert "Manual Host UI: pending" in result.stderr
    assert "Manual Host UI: partial" in result.stderr


def test_host_acceptance_report_freshness_check_cli_runs_as_script(tmp_path: Path) -> None:
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

    result = subprocess.run(  # noqa: S603 - regression test for direct script execution with a static command.
        [
            sys.executable,
            "scripts/check_host_acceptance_report.py",
            "--report",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "host acceptance evidence is fresh" in result.stdout


def test_host_acceptance_report_freshness_check_cli_uses_root_default_report(tmp_path: Path) -> None:
    _write_minimal_release_metadata(tmp_path)
    docs_path = tmp_path / "docs"
    output_path = docs_path / "HOST_ACCEPTANCE_EVIDENCE.md"
    docs_path.mkdir()
    (docs_path / "HOST_MANUAL_RUNS.json").write_text('{"manual_host_ui": []}', encoding="utf-8")

    subprocess.run(  # noqa: S603 - regression test for direct script execution with a static command.
        [
            sys.executable,
            "scripts/export_host_acceptance_report.py",
            "--root",
            str(tmp_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(  # noqa: S603 - regression test for direct script execution with a static command.
        [
            sys.executable,
            "scripts/check_host_acceptance_report.py",
            "--root",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert f"host acceptance evidence is fresh: {output_path}" in result.stdout


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


def _write_codex_manual_run(path: Path) -> None:
    path.write_text(
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
