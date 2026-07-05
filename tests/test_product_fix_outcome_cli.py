from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from tests.test_product_fix_implementation_plan_cli import _write_empty_records, _write_ready_records


def _append_beta_record(beta_records: Path, record: dict[str, Any]) -> None:
    payload = json.loads(beta_records.read_text(encoding="utf-8"))
    payload["records"].append(record)
    beta_records.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_accepted_outcome_records(tmp_path: Path) -> tuple[Path, Path]:
    host_records, beta_records = _write_ready_records(tmp_path)
    _append_beta_record(
        beta_records,
        {
            "workflow_id": "noisy_preview_tuning",
            "status": "passed",
            "attempt_date": "2026-07-06",
            "participant_role": "ML practitioner",
            "summary": "Post-fix noisy preview retry kept the objects recognizable while preserving useful variation.",
            "triage_bucket": "review_agent_v3_gap",
            "artifact_refs": ["docs/assets/demo/demo_report.md"],
            "private_data_included": False,
        },
    )
    return host_records, beta_records


def _write_rejected_outcome_records(tmp_path: Path) -> tuple[Path, Path]:
    host_records, beta_records = _write_ready_records(tmp_path)
    _append_beta_record(
        beta_records,
        {
            "workflow_id": "noisy_preview_tuning",
            "status": "blocked",
            "attempt_date": "2026-07-06",
            "participant_role": "ML practitioner",
            "summary": "Post-fix noisy preview retry still made target objects unreadable.",
            "triage_bucket": "review_agent_v3_gap",
            "artifact_refs": ["docs/assets/demo/demo_report.md"],
            "private_data_included": False,
        },
    )
    return host_records, beta_records


def test_activation_product_fix_outcome_blocks_without_validated_fix(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["outcome_status"] == "blocked_until_product_fix_validation"
    assert payload["validation_status"] == "blocked_until_execution_guard"
    assert payload["writes_records"] is False
    assert payload["evidence_sufficient"] is False
    assert payload["fix_accepted"] is False
    assert payload["fix_rejected"] is False
    assert payload["outcome_evidence"] is None
    assert "p0_host_evidence_missing_or_blocked" in payload["blocked_reasons"]
    assert "albu-mcp activation product-fix-validation --host Codex --format json" in payload["next_commands"]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_activation_product_fix_outcome_accepts_validated_fix_with_passed_bucket_signal(tmp_path: Path) -> None:
    host_records, beta_records = _write_accepted_outcome_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    evidence = payload["outcome_evidence"]

    assert payload["outcome_status"] == "accepted"
    assert payload["validation_status"] == "validated"
    assert payload["fix_validated"] is True
    assert payload["evidence_sufficient"] is True
    assert payload["fix_accepted"] is True
    assert payload["fix_rejected"] is False
    assert payload["selected_fix"]["triage_bucket"] == "review_agent_v3_gap"
    assert payload["blocked_reasons"] == []
    assert evidence["triage_bucket"] == "review_agent_v3_gap"
    assert evidence["status_counts"] == {"blocked": 0, "needs_followup": 1, "passed": 1}
    assert [record["status"] for record in evidence["accepted_records"]] == ["passed"]
    assert [record["status"] for record in evidence["open_records"]] == ["needs_followup"]
    assert "docs/assets/demo/demo_report.md" in evidence["artifact_refs"]
    assert "albu-mcp activation product-fix-outcome --host Codex --format markdown" in payload["next_commands"]

    markdown_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Outcome status: `accepted`" in markdown_result.stdout
    assert "Fix accepted: `true`" in markdown_result.stdout


def test_activation_product_fix_outcome_rejects_blocked_bucket_signal(tmp_path: Path) -> None:
    host_records, beta_records = _write_rejected_outcome_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["outcome_status"] == "rejected"
    assert payload["fix_accepted"] is False
    assert payload["fix_rejected"] is True
    assert payload["evidence_sufficient"] is True
    assert payload["outcome_evidence"]["status_counts"] == {"blocked": 1, "needs_followup": 1, "passed": 0}
    assert payload["blocked_reasons"] == ["post_fix_beta_blocked:review_agent_v3_gap"]
    assert "albu-mcp activation first-product-fix --host Codex --format json" in payload["next_commands"]


def test_activation_product_fix_outcome_writes_markdown_artifacts(tmp_path: Path) -> None:
    host_records, beta_records = _write_accepted_outcome_records(tmp_path)
    output_dir = tmp_path / "product-fix-outcome"
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    expected_files = {
        "outcome-decision.md",
        "outcome-evidence.md",
        "product-fix-outcome-index.md",
    }
    index = (output_dir / "product-fix-outcome-index.md").read_text(encoding="utf-8")
    evidence = (output_dir / "outcome-evidence.md").read_text(encoding="utf-8")
    decision = (output_dir / "outcome-decision.md").read_text(encoding="utf-8")

    assert (
        result.stdout == f"wrote activation product-fix-outcome with {len(expected_files)} artifacts to {output_dir}\n"
    )
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "Outcome status: `accepted`" in index
    assert "Fix accepted: `true`" in index
    assert "review_agent_v3_gap" in evidence
    assert "Post-fix noisy preview retry kept the objects recognizable" in evidence
    assert "Evidence sufficient: `true`" in decision
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
