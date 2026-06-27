import json
import subprocess
import sys
from pathlib import Path

from scripts.verify_host_evidence_import import (
    build_host_evidence_import_guide,
    render_host_evidence_import_guide_markdown,
    verify_host_evidence_import,
)


def test_host_evidence_import_verifies_candidates_without_writing_records(tmp_path: Path) -> None:
    source_path = tmp_path / "candidate-evidence.json"
    records_path = tmp_path / "HOST_MANUAL_RUNS.json"
    records_path.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    before = records_path.read_text(encoding="utf-8")
    source_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "kind": "manual_host_ui",
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-06-28",
                        "evidence": (
                            "Codex host UI listed the MCP tools and run_host_smoke_check returned preview_ready true."
                        ),
                    },
                    {
                        "kind": "first_10_minutes_replay",
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-06-28",
                        "evidence": (
                            "Codex completed smoke, preview validation, render_preview_batch, comparison, and export."
                        ),
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    },
                    {
                        "kind": "manual_host_ui",
                        "host": "Claude Code",
                        "status": "passed",
                        "date": "2026-06-28",
                        "evidence": (
                            "Claude Code listed the MCP tools and completed run_host_smoke_check in the real UI."
                        ),
                    },
                    {
                        "kind": "first_10_minutes_replay",
                        "host": "Claude Code",
                        "status": "passed",
                        "date": "2026-06-28",
                        "evidence": (
                            "Claude Code completed smoke, preview validation, render_preview_batch, comparison, "
                            "and export."
                        ),
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = verify_host_evidence_import(source_path=source_path, records_path=records_path)

    assert report.ok is True
    assert report.import_status == "ready_to_record"
    assert report.write_performed is False
    assert records_path.read_text(encoding="utf-8") == before
    assert report.missing_required_gates == []
    assert len(report.record_commands) == 4
    assert all("scripts/record_host_manual_run.py" in command for command in report.record_commands)
    assert any("--kind first-10-minutes" in command for command in report.record_commands)


def test_host_evidence_import_accepts_canonical_manual_runs_shape(tmp_path: Path) -> None:
    source_path = tmp_path / "canonical-evidence.json"
    source_path.write_text(
        json.dumps(
            {
                "manual_host_ui": [
                    {
                        "host": "Codex",
                        "status": "blocked",
                        "date": "2026-06-28",
                        "evidence": "Codex real host UI could not access the configured artifact root during preview.",
                    }
                ],
                "first_10_minutes_replay": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-06-28",
                        "evidence": (
                            "Codex completed smoke, preview validation, render_preview_batch, comparison, and export."
                        ),
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = verify_host_evidence_import(source_path=source_path)

    assert report.ok is True
    assert report.import_status == "partial_ready_to_record"
    assert report.valid_record_count == 2
    assert ("Claude Code", "manual_host_ui") in report.missing_required_gates
    assert any("--status blocked" in command for command in report.record_commands)


def test_host_evidence_import_rejects_template_or_placeholder_evidence(tmp_path: Path) -> None:
    source_path = tmp_path / "placeholder-evidence.json"
    source_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "kind": "manual_host_ui",
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-06-28",
                        "evidence": "<redacted evidence>",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = verify_host_evidence_import(source_path=source_path)

    assert report.ok is False
    assert report.import_status == "blocked"
    assert report.valid_record_count == 0
    assert report.rejected_records[0]["host"] == "Codex"
    assert "placeholder" in report.rejected_records[0]["issues"][0]
    assert report.record_commands == []


def test_host_evidence_import_cli_emits_json_and_fails_for_rejected_candidates(tmp_path: Path) -> None:
    source_path = tmp_path / "placeholder-evidence.json"
    source_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "kind": "manual_host_ui",
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-06-28",
                        "evidence": "TODO: paste real host evidence",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/verify_host_evidence_import.py",
            "--input",
            str(source_path),
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["ok"] is False
    assert payload["import_status"] == "blocked"
    assert "placeholder" in payload["rejected_records"][0]["issues"][0]


def test_host_evidence_import_guide_markdown_documents_no_write_policy() -> None:
    markdown = render_host_evidence_import_guide_markdown(build_host_evidence_import_guide())

    assert "# P0 Evidence Import Guide" in markdown
    assert "verify-only" in markdown
    assert "does not write `docs/HOST_MANUAL_RUNS.json`" in markdown
    assert "uv run python scripts/verify_host_evidence_import.py" in markdown
