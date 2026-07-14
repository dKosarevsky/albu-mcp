import json
import subprocess
import sys
from pathlib import Path

from scripts.check_host_proof_sprint import HostProofSprintConfig, check_host_proof_sprint


def test_host_proof_sprint_accepts_current_runbook_and_links() -> None:
    report = check_host_proof_sprint()

    assert report.ok is True
    assert [check.name for check in report.checks] == [
        "runbook",
        "manual_runs_schema",
        "documentation_index_link",
        "acceptance_docs",
    ]
    assert all(check.message for check in report.checks)


def test_host_proof_sprint_reports_missing_documentation_index_link(tmp_path: Path) -> None:
    documentation_index = _write_text(tmp_path / "docs" / "INDEX.md", "# Documentation Index\n")
    runbook = _write_text(tmp_path / "docs" / "HOST_PROOF_SPRINT.md", _valid_runbook_text())
    schema = _write_text(tmp_path / "docs" / "HOST_MANUAL_RUNS.schema.json", _valid_schema_text())
    acceptance = _write_text(tmp_path / "docs" / "HOST_ACCEPTANCE.md", _valid_acceptance_text())

    report = check_host_proof_sprint(
        HostProofSprintConfig(
            documentation_index_path=documentation_index,
            runbook_path=runbook,
            manual_runs_schema_path=schema,
            host_acceptance_path=acceptance,
        )
    )

    assert report.ok is False
    assert report.by_name["documentation_index_link"].ok is False
    assert "HOST_PROOF_SPRINT.md" in report.by_name["documentation_index_link"].message


def test_host_proof_sprint_cli_outputs_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_host_proof_sprint.py",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["checks"][0]["name"] == "runbook"


def test_host_proof_status_records_v116_machine_and_codex_host_proof() -> None:
    status = Path("docs/HOST_PROOF_STATUS.md").read_text(encoding="utf-8")

    assert "v1.18.0" in status
    assert "review_packet_flow: ok" in status
    assert "dataset_quality_inspection_flow: ok" in status
    assert "Codex Manual Host UI: passed on 2026-07-11" in status
    assert "Codex First 10 Minutes Replay: passed on 2026-07-11" in status
    assert "Claude Code Manual Host UI: blocked" in status
    assert 'scripts/check_first_10_minutes_replay.py --host Codex --host "Claude Code"' in status
    assert "client_smoke_resource_flow: ok" in status
    assert "albumentationsx-mcp-1.18.0.mcpb" in status
    assert "albumentationsx-mcp.mcpb" in status


def _valid_runbook_text() -> str:
    return """# Host Proof Sprint
docs/FIRST_10_MINUTES.md
examples/first_10_minutes_prompt.md
scripts/export_manual_host_acceptance_packet.py
scripts/record_host_manual_run.py --kind first-10-minutes
scripts/check_first_10_minutes_replay.py
docs/HOST_ACCEPTANCE_EVIDENCE.md
Codex
Claude Code
"""


def _valid_schema_text() -> str:
    return json.dumps(
        {
            "properties": {
                "first_10_minutes_replay": {
                    "items": {
                        "properties": {
                            "artifacts": {"type": "array"},
                        }
                    }
                }
            }
        }
    )


def _valid_acceptance_text() -> str:
    return """# Host Acceptance Checklist
scripts/check_first_10_minutes_replay.py
--kind first-10-minutes
"""


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
