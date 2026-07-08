from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_host_trust_dashboard_reports_one_next_action_per_host(tmp_path: Path) -> None:
    from albumentationsx_mcp.host_trust import build_host_trust_dashboard

    host_records = _write_blocked_host_records(tmp_path)

    report = build_host_trust_dashboard(path=host_records)

    assert report["dashboard_status"] == "blocked"
    assert report["execution_policy"] == "report_only"
    assert report["records_path"] == str(host_records)
    assert report["next_host"] == "Codex"
    assert report["next_command"] == (
        "albu-mcp evidence collect --host Codex --date YYYY-MM-DD --reviewer '<reviewer>' --format markdown"
    )

    by_host = {lane["host"]: lane for lane in report["host_lanes"]}
    assert by_host["Codex"]["priority"] == "p0"
    assert by_host["Codex"]["overall_status"] == "blocked"
    assert by_host["Codex"]["next_gate"] == "first_10_minutes_replay"
    assert by_host["Codex"]["next_action_code"] == "triage_blocker"
    assert by_host["Codex"]["gate_statuses"] == {
        "manual_host_ui": "blocked",
        "first_10_minutes_replay": "blocked",
    }
    assert by_host["Claude Desktop"]["priority"] == "p1"
    assert by_host["Claude Desktop"]["overall_status"] == "pending"
    assert by_host["Claude Desktop"]["next_action_code"] == "collect_real_host_evidence"
    assert by_host["Claude Desktop"]["gate_statuses"] == {
        "manual_host_ui": "missing",
        "first_10_minutes_replay": "missing",
    }


def test_host_trust_dashboard_can_include_guided_session_payload(tmp_path: Path) -> None:
    from albumentationsx_mcp.host_trust import build_host_trust_dashboard

    host_records = _write_blocked_host_records(tmp_path)

    report = build_host_trust_dashboard(path=host_records, host="Codex", include_session=True)

    session = report["guided_session"]
    assert session["host"] == "Codex"
    assert session["next_gate"] == "first_10_minutes_replay"
    assert session["writes_records"] is False
    assert session["manifest_path"] == "docs/operator-packets/codex-evidence-session-manifest.json"
    assert session["commands"] == {
        "collect": "albu-mcp evidence collect --host Codex --date YYYY-MM-DD --reviewer '<reviewer>' --format markdown",
        "session_manifest": (
            "albu-mcp evidence session-manifest --host Codex --date YYYY-MM-DD "
            "--reviewer '<reviewer>' --output-dir docs/operator-packets --format json"
        ),
        "validate_manifest": (
            "albu-mcp evidence validate-manifest "
            "--input docs/operator-packets/codex-evidence-session-manifest.json --format json"
        ),
        "import_artifacts": (
            "albu-mcp evidence import-artifacts --host Codex --status passed --date YYYY-MM-DD "
            "--evidence '<redacted reviewer-observed evidence>' --artifact docs/assets/demo/demo_report.md "
            "--confirm-real-host-observed"
        ),
        "privacy_doctor": "albu-mcp evidence privacy-doctor --format json",
        "artifact_doctor": "albu-mcp evidence artifact-doctor --format json",
        "regenerate_dashboard": (
            "albu-mcp host next-action --include-session --format markdown --output docs/HOST_TRUST_DASHBOARD.md"
        ),
    }
    assert session["stop_conditions"] == [
        "Do not run import_artifacts until a reviewer observes the real MCP host UI session.",
        "Do not record passed evidence without --confirm-real-host-observed.",
        "Do not commit private dataset paths or file:// artifact references.",
        "Do not treat generated smoke output as manual host evidence.",
    ]


def test_host_next_action_cli_outputs_json_for_operator_dashboard(tmp_path: Path) -> None:
    host_records = _write_blocked_host_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "host",
            "next-action",
            "--path",
            str(host_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["dashboard_status"] == "blocked"
    assert payload["next_host"] == "Codex"
    assert payload["host_lanes"][0]["host"] == "Codex"
    assert payload["host_lanes"][0]["next_action_code"] == "triage_blocker"


def test_host_next_action_cli_can_include_guided_session_json(tmp_path: Path) -> None:
    host_records = _write_blocked_host_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "host",
            "next-action",
            "--path",
            str(host_records),
            "--host",
            "Codex",
            "--include-session",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["next_host"] == "Codex"
    assert payload["guided_session"]["host"] == "Codex"
    assert payload["guided_session"]["commands"]["validate_manifest"] == (
        "albu-mcp evidence validate-manifest "
        "--input docs/operator-packets/codex-evidence-session-manifest.json --format json"
    )
    assert payload["guided_session"]["commands"]["privacy_doctor"] == "albu-mcp evidence privacy-doctor --format json"


def test_host_next_action_cli_writes_markdown_dashboard(tmp_path: Path) -> None:
    host_records = _write_blocked_host_records(tmp_path)
    output = tmp_path / "HOST_TRUST_DASHBOARD.md"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "host",
            "next-action",
            "--path",
            str(host_records),
            "--format",
            "markdown",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    content = output.read_text(encoding="utf-8")

    assert result.stdout == f"wrote host trust dashboard to {output}\n"
    assert "# Host Trust Dashboard" in content
    assert "| Host | Priority | Overall | Manual Host UI | First 10 Minutes | Next Action | Next Command |" in content
    assert "| Codex | `p0` | `blocked` | `blocked` | `blocked` | Triage blocker |" in content
    assert "albu-mcp host next-action --format markdown --output docs/HOST_TRUST_DASHBOARD.md" in content
    assert "does not write evidence records" in content


def test_host_next_action_cli_writes_guided_session_markdown(tmp_path: Path) -> None:
    host_records = _write_blocked_host_records(tmp_path)
    output = tmp_path / "HOST_TRUST_DASHBOARD.md"

    subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "host",
            "next-action",
            "--path",
            str(host_records),
            "--host",
            "Codex",
            "--include-session",
            "--format",
            "markdown",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    content = output.read_text(encoding="utf-8")

    assert "## Guided Session" in content
    assert "`manifest_path`: `docs/operator-packets/codex-evidence-session-manifest.json`" in content
    assert (
        "albu-mcp evidence validate-manifest --input docs/operator-packets/codex-evidence-session-manifest.json"
        in content
    )
    assert "Do not record passed evidence without --confirm-real-host-observed." in content


def test_committed_host_trust_dashboard_is_lightweight_and_regenerable() -> None:
    content = Path("docs/HOST_TRUST_DASHBOARD.md").read_text(encoding="utf-8")

    assert "# Host Trust Dashboard" in content
    assert (
        "albu-mcp host next-action --include-session --format markdown --output docs/HOST_TRUST_DASHBOARD.md" in content
    )
    assert "## Guided Session" in content
    assert "docs/HOST_MANUAL_RUNS.json" in content
    assert content.count("| Codex |") == 1


def _write_blocked_host_records(tmp_path: Path) -> Path:
    path = tmp_path / "HOST_MANUAL_RUNS.json"
    path.write_text(
        json.dumps(
            {
                "manual_host_ui": [
                    {
                        "host": "Claude Code",
                        "status": "blocked",
                        "date": "2026-06-28",
                        "evidence": "Claude Code CLI was unavailable in this environment.",
                    },
                    {
                        "host": "Codex",
                        "status": "blocked",
                        "date": "2026-06-28",
                        "evidence": "Codex setup passed, but no reviewer-observed real MCP host UI completed.",
                    },
                ],
                "first_10_minutes_replay": [
                    {
                        "host": "Claude Code",
                        "status": "blocked",
                        "date": "2026-06-28",
                        "evidence": "Claude Code first-10-minutes replay was not executed.",
                        "artifacts": ["docs/operator-packets/albu-host-Claude-Code.md"],
                    },
                    {
                        "host": "Codex",
                        "status": "blocked",
                        "date": "2026-06-28",
                        "evidence": "Codex first-10-minutes replay was not executed.",
                        "artifacts": ["docs/operator-packets/albu-host-Codex.md"],
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path
