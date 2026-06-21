import subprocess
import sys
from pathlib import Path


def test_published_package_smoke_dry_run_uses_release_metadata(tmp_path: Path) -> None:
    _write_minimal_release_metadata(tmp_path)

    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "scripts/check_published_package_smoke.py",
            "--root",
            str(tmp_path),
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == (
        "uvx --from albumentationsx-mcp==9.9.9 "
        "--refresh-package albumentationsx-mcp albumentationsx-mcp --help"
    )


def test_host_acceptance_report_includes_published_package_smoke() -> None:
    from scripts.export_host_acceptance_report import build_host_acceptance_report, dump_host_acceptance_markdown

    report = build_host_acceptance_report(Path())
    markdown = dump_host_acceptance_markdown(report)

    assert "published package smoke" in {item["name"] for item in report["automated_coverage"]}
    assert "scripts/check_published_package_smoke.py" in markdown


def test_published_package_smoke_builds_direct_pypi_version_url() -> None:
    from scripts.check_published_package_smoke import build_pypi_version_url

    assert build_pypi_version_url(package="albumentationsx-mcp", version="1.13.0") == (
        "https://pypi.org/pypi/albumentationsx-mcp/1.13.0/json"
    )


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
