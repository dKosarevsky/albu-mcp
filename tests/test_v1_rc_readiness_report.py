from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.export_v1_rc_readiness_report import build_v1_rc_readiness_report, render_v1_rc_readiness_report_markdown


def test_v1_rc_readiness_report_holds_until_p0_hosts_pass() -> None:
    report = build_v1_rc_readiness_report()

    assert report["rc_decision"] == "hold_rc"
    assert report["rc_release_candidate_allowed"] is False
    assert report["stable_v1_allowed"] is False
    assert report["required_rc_hosts"] == ["Codex", "Claude Code"]
    assert [item["host"] for item in report["rc_blockers"][:2]] == ["Codex", "Codex"]
    assert {item["gate"] for item in report["rc_blockers"]} == {"first_10_minutes_replay", "manual_host_ui"}
    assert report["policy"] == "RC requires real P0 host evidence; stable v1 requires every supported host gate."
    assert (
        "uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md"
        in report["next_checks"]
    )


def test_v1_rc_readiness_report_markdown_is_reviewable() -> None:
    markdown = render_v1_rc_readiness_report_markdown(build_v1_rc_readiness_report())

    assert markdown.startswith("# V1 RC Readiness Report\n")
    assert "RC decision: `hold_rc`" in markdown
    assert "RC release candidate allowed: `false`" in markdown
    assert "Stable v1 allowed: `false`" in markdown
    assert "## RC Blockers" in markdown
    assert "| Codex | `p0` | `first_10_minutes_replay` | `blocked` | `triage_blocker` |" in markdown
    assert "## Promotion Rule" in markdown
    assert "Stable v1 requires all supported hosts to pass." in markdown


def test_v1_rc_readiness_report_cli_outputs_json_and_markdown(tmp_path: Path) -> None:
    json_result = subprocess.run(
        [sys.executable, "scripts/export_v1_rc_readiness_report.py", "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(json_result.stdout)["rc_decision"] == "hold_rc"

    output_path = tmp_path / "v1-rc-readiness.md"
    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_v1_rc_readiness_report.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "RC decision: `hold_rc`" in output_path.read_text(encoding="utf-8")


def test_committed_v1_rc_readiness_report_is_current() -> None:
    report_path = Path("docs/V1_RC_READINESS.md")

    assert report_path.read_text(encoding="utf-8") == render_v1_rc_readiness_report_markdown(
        build_v1_rc_readiness_report()
    )
    assert "[docs/V1_RC_READINESS.md](docs/V1_RC_READINESS.md)" in Path("README.md").read_text(encoding="utf-8")
