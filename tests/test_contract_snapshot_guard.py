import subprocess
import sys
from pathlib import Path

from scripts.check_contract_snapshots import check_contract_snapshots


def test_contract_snapshot_guard_accepts_current_committed_snapshots(tmp_path: Path) -> None:
    report = check_contract_snapshots(output_work_dir=tmp_path)

    assert report.ok is True
    assert {check.name for check in report.checks} == {"mcp_contract", "output_contracts"}
    assert all(check.diff == "" for check in report.checks)


def test_contract_snapshot_guard_reports_stale_mcp_contract_diff(tmp_path: Path) -> None:
    stale_mcp = tmp_path / "mcp_contract.json"
    stale_mcp.write_text('{"server": {"name": "stale"}}\n', encoding="utf-8")

    report = check_contract_snapshots(
        mcp_snapshot_path=stale_mcp,
        output_snapshot_path=Path("tests/fixtures/snapshots/output_contracts.json"),
        output_work_dir=tmp_path / "outputs",
    )
    mcp_check = next(check for check in report.checks if check.name == "mcp_contract")

    assert report.ok is False
    assert mcp_check.ok is False
    assert "MCP contract snapshot is stale" in mcp_check.message
    assert "---" in mcp_check.diff
    assert "+++" in mcp_check.diff
    assert "stale" in mcp_check.diff
    assert "AlbumentationsX MCP" in mcp_check.diff


def test_contract_snapshot_guard_cli_prints_stale_diff(tmp_path: Path) -> None:
    stale_mcp = tmp_path / "mcp_contract.json"
    stale_mcp.write_text('{"server": {"name": "stale"}}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/check_contract_snapshots.py",
            "--mcp-snapshot",
            str(stale_mcp),
            "--output-snapshot",
            "tests/fixtures/snapshots/output_contracts.json",
            "--output-work-dir",
            str(tmp_path / "outputs"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "MCP contract snapshot is stale" in result.stderr
    assert "---" in result.stderr
    assert "+++" in result.stderr
    assert "stale" in result.stderr
    assert "AlbumentationsX MCP" in result.stderr
