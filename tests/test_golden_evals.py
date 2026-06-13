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
    assert {scenario["name"] for scenario in scenarios["scenarios"]} == {
        "classification_recommend_validate_explain_export",
        "preview_lifecycle",
    }


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
    assert "classification_recommend_validate_explain_export: ok" in completed.stdout
    assert "preview_lifecycle: ok" in completed.stdout
