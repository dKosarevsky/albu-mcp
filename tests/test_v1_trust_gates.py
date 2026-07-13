from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.export_v1_trust_gates import build_v1_trust_gates, render_v1_trust_gates_markdown


def test_v1_trust_gates_separate_automated_and_manual_gates() -> None:
    report = build_v1_trust_gates()
    markdown = render_v1_trust_gates_markdown(report)

    assert report["ready_for_v1"] is False
    assert report["manual_evidence_required"] is True
    assert {gate["code"] for gate in report["automated_gates"]} == {
        "release_readiness",
        "host_proof_sprint_docs",
        "v1_launch_report",
    }
    assert len(report["manual_gates"]) == 5
    assert {gate["status"] for gate in report["manual_gates"]} == {"blocked", "pending"}
    assert {(gate["host"], gate["kind"]): gate["status"] for gate in report["manual_gates"]} == {
        ("Claude Code", "manual Host UI evidence"): "blocked",
        ("Cursor", "manual Host UI evidence"): "pending",
        ("Claude Desktop", "first 10 minutes replay"): "pending",
        ("Claude Code", "first 10 minutes replay"): "blocked",
        ("Cursor", "first 10 minutes replay"): "pending",
    }
    assert "Do not cut v1.0.0" in markdown
    assert "manual Host UI evidence" in markdown
    assert "first 10 minutes replay" in markdown


def test_committed_v1_trust_gates_are_current() -> None:
    trust_gates_path = Path("docs/V1_TRUST_GATES.md")

    assert trust_gates_path.read_text(encoding="utf-8") == render_v1_trust_gates_markdown(build_v1_trust_gates())
    assert "docs/V1_TRUST_GATES.md" in Path("docs/V1_READINESS.md").read_text(encoding="utf-8")


def test_v1_trust_gates_cli_outputs_json_and_markdown(tmp_path: Path) -> None:
    json_result = subprocess.run(
        [sys.executable, "scripts/export_v1_trust_gates.py", "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(json_result.stdout)
    assert payload["manual_evidence_required"] is True

    output_path = tmp_path / "trust-gates.md"
    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_v1_trust_gates.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert output_path.read_text(encoding="utf-8").startswith("# V1 Trust Gates\n")
