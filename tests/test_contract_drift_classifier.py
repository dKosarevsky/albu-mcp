import json
import subprocess
import sys
from pathlib import Path

from scripts.classify_contract_drift import classify_contract_drift


def test_contract_drift_classifier_reports_no_change() -> None:
    result = classify_contract_drift({"tools": [{"name": "render_preview"}]}, {"tools": [{"name": "render_preview"}]})

    assert result.kind == "no_change"
    assert result.paths == []


def test_contract_drift_classifier_reports_compatible_addition() -> None:
    result = classify_contract_drift(
        {"resources": [{"uri": "albumentationsx://capabilities"}]},
        {
            "resources": [
                {"uri": "albumentationsx://capabilities"},
                {"uri": "albumentationsx://examples/distortion-review"},
            ]
        },
    )

    assert result.kind == "compatible_addition"
    assert result.paths == ["resources[1]"]


def test_contract_drift_classifier_reports_documentation_only_change() -> None:
    result = classify_contract_drift(
        {"tools": [{"name": "render_preview", "description": "old"}]},
        {"tools": [{"name": "render_preview", "description": "new"}]},
    )

    assert result.kind == "documentation_only"
    assert result.paths == ["tools[render_preview].description"]


def test_contract_drift_classifier_reports_breaking_change() -> None:
    result = classify_contract_drift(
        {"tools": [{"name": "render_preview"}, {"name": "export_pipeline"}]},
        {"tools": [{"name": "render_preview"}]},
    )

    assert result.kind == "breaking_change"
    assert result.paths == ["tools[export_pipeline]"]


def test_contract_drift_classifier_reports_output_shape_change() -> None:
    result = classify_contract_drift(
        {"preview_report": {"quality_summary": {"score": 95}}},
        {"preview_report": {"quality_summary": {"score": 90}}},
    )

    assert result.kind == "output_shape_change"
    assert result.paths == ["preview_report.quality_summary.score"]


def test_contract_drift_classifier_cli_emits_json(tmp_path: Path) -> None:
    committed = tmp_path / "committed.json"
    generated = tmp_path / "generated.json"
    committed.write_text(json.dumps({"server": {"description": "old"}}), encoding="utf-8")
    generated.write_text(json.dumps({"server": {"description": "new"}}), encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/classify_contract_drift.py",
            "--committed",
            str(committed),
            "--generated",
            str(generated),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["kind"] == "documentation_only"
    assert payload["paths"] == ["server.description"]
