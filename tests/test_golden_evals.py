from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image


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
    diagnostics_scenario = next(
        scenario for scenario in scenarios["scenarios"] if scenario["name"] == "diagnostics_resource_flow"
    )
    first_preview_scenario = next(
        scenario for scenario in scenarios["scenarios"] if scenario["name"] == "first_preview_resource_prompt_flow"
    )
    real_sample_scenario = next(
        scenario for scenario in scenarios["scenarios"] if scenario["name"] == "real_sample_preview_smoke"
    )
    preview_request_scenario = next(
        scenario for scenario in scenarios["scenarios"] if scenario["name"] == "preview_request_troubleshooting"
    )
    interactive_session_scenario = next(
        scenario for scenario in scenarios["scenarios"] if scenario["name"] == "interactive_tuning_session_flow"
    )

    assert {scenario["name"] for scenario in scenarios["scenarios"]} == {
        "client_smoke_resource_flow",
        "diagnostics_resource_flow",
        "first_preview_resource_prompt_flow",
        "classification_recommend_validate_explain_export",
        "preview_lifecycle",
        "preview_batch_compare",
        "preview_quality_tuning_summary",
        "real_sample_preview_smoke",
        "preview_request_troubleshooting",
        "interactive_tuning_session_flow",
    }
    assert smoke_scenario["client_smoke"] is True
    assert smoke_scenario["smoke_resources"] == [
        "albumentationsx://examples/client-smoke",
        "albumentationsx://capabilities",
        "albumentationsx://recipes/catalog",
    ]
    assert smoke_scenario["host_smoke"] is True
    assert diagnostics_scenario["diagnostics_smoke"] is True
    assert diagnostics_scenario["diagnostics_resources"] == [
        "albumentationsx://diagnostics/guide",
        "albumentationsx://capabilities",
    ]
    assert first_preview_scenario["first_preview_smoke"] is True
    assert real_sample_scenario["real_sample_smoke"] is True
    assert real_sample_scenario["input_count"] == 3
    assert real_sample_scenario["compare_preview"] is True
    assert preview_request_scenario["preview_request_troubleshooting"] is True
    assert interactive_session_scenario["interactive_tuning_session"] is True
    assert interactive_session_scenario["accepted"] is True
    assert interactive_session_scenario["export_session_preview_report"] is True
    assert quality_scenario["record_preview_feedback"] is True
    assert quality_scenario["feedback_image_index"] == 7
    assert quality_scenario["assert_preview_report_feedback"] is True
    assert "_run_client_smoke" in runner_source
    assert "_run_diagnostics_smoke" in runner_source
    assert "_run_first_preview_smoke" in runner_source
    assert "_run_real_sample_smoke" in runner_source
    assert "_run_preview_request_troubleshooting" in runner_source
    assert "_run_interactive_tuning_session" in runner_source
    assert "run_host_smoke_check" in runner_source
    assert "validate_preview_request" in runner_source
    real_sample_source = runner_source.split("async def _run_real_sample_smoke", maxsplit=1)[1].split(
        "async def _run_preview_request_troubleshooting",
        maxsplit=1,
    )[0]
    preview_comparison_source = runner_source.split("async def _run_preview_comparison", maxsplit=1)[1].split(
        "async def _run_candidate_ranking",
        maxsplit=1,
    )[0]
    assert "_validate_preview_request_or_fail" in real_sample_source
    assert "_validate_preview_request_or_fail" in preview_comparison_source
    assert "_read_resource_json" in runner_source
    assert "record_preview_feedback" in runner_source
    assert "assert_preview_report_feedback" in runner_source


def test_real_sample_smoke_inputs_are_non_uniform_rgb_images(tmp_path: Path) -> None:
    from scripts.run_golden_evals import _write_real_sample_inputs

    paths = _write_real_sample_inputs(tmp_path, {"name": "real_sample_preview_smoke", "input_count": 3})

    assert len(paths) == 3
    for path in paths:
        assert path.parent == tmp_path / "real-sample-preview-smoke"
        assert path.suffix == ".png"
        image = Image.open(path)
        assert image.mode == "RGB"
        pixels = np.asarray(image)
        assert pixels.shape == (96, 128, 3)
        assert int(pixels.max()) > int(pixels.min())
        assert len({tuple(pixel) for row in pixels for pixel in row}) > 16


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
    assert "diagnostics_resource_flow: ok" in completed.stdout
    assert "classification_recommend_validate_explain_export: ok" in completed.stdout
    assert "preview_lifecycle: ok" in completed.stdout
    assert "first_preview_resource_prompt_flow: ok" in completed.stdout
    assert "preview_batch_compare: ok" in completed.stdout
    assert "preview_quality_tuning_summary: ok" in completed.stdout
    assert "real_sample_preview_smoke: ok" in completed.stdout
    assert "preview_request_troubleshooting: ok" in completed.stdout
    assert "interactive_tuning_session_flow: ok" in completed.stdout
