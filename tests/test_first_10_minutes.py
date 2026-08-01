import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_first_10_minutes import FirstTenMinutesConfig, check_first_10_minutes


def test_first_10_minutes_accepts_current_entrypoints() -> None:
    report = check_first_10_minutes()

    assert report.ok is True
    assert [check.name for check in report.checks] == [
        "readme_entrypoint",
        "quickstart_guide",
        "host_prompt",
        "demo_artifacts",
    ]
    assert all(check.message for check in report.checks)


def test_first_10_minutes_reports_missing_readme_link(tmp_path: Path) -> None:
    readme = _write_text(tmp_path / "README.md", "# AlbumentationsX MCP\n")
    guide = _write_text(tmp_path / "docs" / "FIRST_10_MINUTES.md", _valid_guide_text())
    prompt = _write_text(tmp_path / "examples" / "first_10_minutes_prompt.md", _valid_prompt_text())
    manifest = _write_text(
        tmp_path / "docs" / "assets" / "demo" / "demo_manifest.json",
        json.dumps({"workflow": "distortion_review", "demo_report": "demo_report.md"}),
    )
    report_md = _write_text(tmp_path / "docs" / "assets" / "demo" / "demo_report.md", "# Demo Report\n")

    report = check_first_10_minutes(
        FirstTenMinutesConfig(
            readme_path=readme,
            guide_path=guide,
            prompt_path=prompt,
            demo_manifest_path=manifest,
            demo_report_path=report_md,
        )
    )

    assert report.ok is False
    assert report.by_name["readme_entrypoint"].ok is False
    assert "docs/FIRST_10_MINUTES.md" in report.by_name["readme_entrypoint"].message


def test_first_10_minutes_cli_outputs_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_first_10_minutes.py",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["checks"][0]["name"] == "readme_entrypoint"


def test_first_10_minutes_cli_prints_failed_check(tmp_path: Path) -> None:
    readme = _write_text(tmp_path / "README.md", "# AlbumentationsX MCP\n")
    guide = _write_text(tmp_path / "docs" / "FIRST_10_MINUTES.md", _valid_guide_text())
    prompt = _write_text(tmp_path / "examples" / "first_10_minutes_prompt.md", _valid_prompt_text())
    manifest = _write_text(
        tmp_path / "docs" / "assets" / "demo" / "demo_manifest.json",
        json.dumps({"workflow": "distortion_review", "demo_report": "demo_report.md"}),
    )
    report_md = _write_text(tmp_path / "docs" / "assets" / "demo" / "demo_report.md", "# Demo Report\n")

    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/check_first_10_minutes.py",
            "--readme",
            str(readme),
            "--guide",
            str(guide),
            "--prompt",
            str(prompt),
            "--demo-manifest",
            str(manifest),
            "--demo-report",
            str(report_md),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "[readme_entrypoint]" in result.stderr
    assert "docs/FIRST_10_MINUTES.md" in result.stderr


@pytest.mark.parametrize("document_name", ["guide", "prompt"])
@pytest.mark.parametrize(
    "missing_phrases",
    [
        ("run_first_preview",),
        ("trace_preview_variant",),
        ("run_first_preview", "trace_preview_variant"),
    ],
)
def test_first_10_minutes_reports_missing_guided_preview_tools(
    tmp_path: Path,
    document_name: str,
    missing_phrases: tuple[str, ...],
) -> None:
    guide_text = _valid_guide_text()
    prompt_text = _valid_prompt_text()
    if document_name == "guide":
        for phrase in missing_phrases:
            guide_text = guide_text.replace(f"{phrase}\n", "")
    else:
        for phrase in missing_phrases:
            prompt_text = prompt_text.replace(f"{phrase}\n", "")

    report = check_first_10_minutes(_valid_config(tmp_path, guide_text=guide_text, prompt_text=prompt_text))

    check_name = "quickstart_guide" if document_name == "guide" else "host_prompt"
    assert report.ok is False
    assert report.by_name[check_name].ok is False
    for phrase in missing_phrases:
        assert phrase in report.by_name[check_name].message


def _valid_guide_text() -> str:
    return """# First 10 Minutes
uvx --from albumentationsx-mcp albumentationsx-mcp
examples/first_10_minutes_prompt.md
docs/assets/demo/demo_report.md
run_host_smoke_check
run_first_preview
trace_preview_variant
plan_dataset_onboarding
validate_preview_request
render_preview_batch
compare_preview_runs
export_pipeline
docs/INSTALL.md
docs/USAGE.md
"""


def _valid_prompt_text() -> str:
    return """# First 10 Minutes Host Prompt
run_host_smoke_check
run_first_preview
trace_preview_variant
plan_dataset_onboarding
Do not render anything until validate_preview_request returns valid=true.
render_preview_batch
compare_preview_runs
export_pipeline
docs/assets/demo/demo_report.md
"""


def _valid_config(tmp_path: Path, *, guide_text: str, prompt_text: str) -> FirstTenMinutesConfig:
    readme = _write_text(tmp_path / "README.md", "[guide](docs/FIRST_10_MINUTES.md)\n")
    guide = _write_text(tmp_path / "docs" / "FIRST_10_MINUTES.md", guide_text)
    prompt = _write_text(tmp_path / "examples" / "first_10_minutes_prompt.md", prompt_text)
    manifest = _write_text(
        tmp_path / "docs" / "assets" / "demo" / "demo_manifest.json",
        json.dumps({"workflow": "distortion_review", "demo_report": "demo_report.md"}),
    )
    report = _write_text(tmp_path / "docs" / "assets" / "demo" / "demo_report.md", "# Demo Report\n")
    return FirstTenMinutesConfig(
        readme_path=readme,
        guide_path=guide,
        prompt_path=prompt,
        demo_manifest_path=manifest,
        demo_report_path=report,
    )


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
