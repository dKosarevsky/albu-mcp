from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


def test_golden_eval_assets_are_present() -> None:
    scenarios_path = Path("evals/golden_mcp_scenarios.yaml")
    runner_path = Path("scripts/run_golden_evals.py")

    assert scenarios_path.exists()
    assert runner_path.exists()
    scenarios = yaml.safe_load(scenarios_path.read_text(encoding="utf-8"))
    runner_source = runner_path.read_text(encoding="utf-8")
    quality_scenario = next(
        scenario for scenario in scenarios["scenarios"] if scenario["name"] == "preview_quality_tuning_summary"
    )
    smoke_scenario = next(
        scenario for scenario in scenarios["scenarios"] if scenario["name"] == "client_smoke_resource_flow"
    )

    assert {scenario["name"] for scenario in scenarios["scenarios"]} == {
        "client_smoke_resource_flow",
        "classification_recommend_validate_explain_export",
        "preview_lifecycle",
        "preview_batch_compare",
        "preview_quality_tuning_summary",
    }
    assert smoke_scenario["client_smoke"] is True
    assert smoke_scenario["smoke_resources"] == [
        "albumentationsx://examples/client-smoke",
        "albumentationsx://capabilities",
        "albumentationsx://recipes/catalog",
    ]
    assert quality_scenario["record_preview_feedback"] is True
    assert quality_scenario["feedback_image_index"] == 7
    assert quality_scenario["assert_preview_report_feedback"] is True
    assert "_run_client_smoke" in runner_source
    assert "_read_resource_json" in runner_source
    assert "record_preview_feedback" in runner_source
    assert "assert_preview_report_feedback" in runner_source


def test_golden_eval_runner_executes_scenarios_over_stdio(tmp_path: Path) -> None:
    completed = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "scripts/run_golden_evals.py",
            "--scenario-file",
            "evals/golden_mcp_scenarios.yaml",
            "--work-dir",
            str(tmp_path),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "client_smoke_resource_flow: ok" in completed.stdout
    assert "classification_recommend_validate_explain_export: ok" in completed.stdout
    assert "preview_lifecycle: ok" in completed.stdout
    assert "preview_batch_compare: ok" in completed.stdout
    assert "preview_quality_tuning_summary: ok" in completed.stdout
