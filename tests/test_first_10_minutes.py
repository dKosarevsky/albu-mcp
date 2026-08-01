import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_first_10_minutes import FirstTenMinutesCheck, FirstTenMinutesConfig, check_first_10_minutes

_FALLBACK_MARKER = "Explicit fallback:"


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


@pytest.mark.parametrize("document_name", ["guide", "prompt"])
def test_first_10_minutes_rejects_guided_tools_only_in_fallback(
    tmp_path: Path,
    document_name: str,
) -> None:
    primary, fallback = _workflow_text(document_name).split(_FALLBACK_MARKER, 1)
    primary = primary.replace("run_first_preview\n", "").replace("trace_preview_variant\n", "")
    malformed = f"{primary}{_FALLBACK_MARKER}\nrun_first_preview\ntrace_preview_variant\n{fallback}"

    check = _workflow_check(tmp_path, document_name=document_name, text=malformed)

    assert check.ok is False
    assert "primary guided workflow" in check.message
    assert "run_first_preview" in check.message
    assert "trace_preview_variant" in check.message


@pytest.mark.parametrize("document_name", ["guide", "prompt"])
def test_first_10_minutes_rejects_wrong_primary_workflow_order(
    tmp_path: Path,
    document_name: str,
) -> None:
    text = _workflow_text(document_name).replace(
        "run_host_smoke_check\nrun_first_preview",
        "run_first_preview\nrun_host_smoke_check",
        1,
    )

    check = _workflow_check(tmp_path, document_name=document_name, text=text)

    assert check.ok is False
    assert "ordered primary workflow" in check.message
    assert "run_host_smoke_check -> run_first_preview" in check.message


@pytest.mark.parametrize("document_name", ["guide", "prompt"])
@pytest.mark.parametrize(
    "profile_statement",
    [
        "",
        "Guided workflow uses the review capability profile with run_first_preview.\n",
    ],
    ids=["missing-compatible-profile", "review-presented-as-guided"],
)
def test_first_10_minutes_rejects_incompatible_guided_profile(
    tmp_path: Path,
    document_name: str,
    profile_statement: str,
) -> None:
    text = _workflow_text(document_name).replace(
        "Guided workflow requires the default full or dataset capability profile.\n",
        profile_statement,
        1,
    )

    check = _workflow_check(tmp_path, document_name=document_name, text=text)

    assert check.ok is False
    assert "full or dataset capability profile" in check.message


@pytest.mark.parametrize("document_name", ["guide", "prompt"])
@pytest.mark.parametrize("failure", ["missing-boundary", "wrong-fallback-order"])
def test_first_10_minutes_requires_explicit_ordered_fallback(
    tmp_path: Path,
    document_name: str,
    failure: str,
) -> None:
    text = _workflow_text(document_name)
    if failure == "missing-boundary":
        text = text.replace(_FALLBACK_MARKER, "Fallback:", 1)
        expected = "explicit fallback marker"
    else:
        primary, fallback = text.split(_FALLBACK_MARKER, 1)
        fallback = fallback.replace("preview_request_template\n", "", 1)
        text = f"{primary}{_FALLBACK_MARKER}{fallback}\npreview_request_template\n"
        expected = "ordered fallback workflow"

    check = _workflow_check(tmp_path, document_name=document_name, text=text)

    assert check.ok is False
    assert expected in check.message


def _valid_guide_text() -> str:
    return """# First 10 Minutes
uvx --from albumentationsx-mcp albumentationsx-mcp
examples/first_10_minutes_prompt.md
docs/assets/demo/demo_report.md
Guided workflow requires the default full or dataset capability profile.
run_host_smoke_check
run_first_preview
contact sheet
trace_preview_variant
adjust_pipeline
compare_preview_runs
export_pipeline
Explicit fallback:
run_host_smoke_check
preview_request_template
plan_dataset_onboarding
Do not render anything until validate_preview_request returns valid=true.
render_preview_batch
contact sheet
trace_preview_variant
adjust_pipeline
compare_preview_runs
export_pipeline
docs/INSTALL.md
docs/USAGE.md
"""


def _valid_prompt_text() -> str:
    return """# First 10 Minutes Host Prompt
Guided workflow requires the default full or dataset capability profile.
run_host_smoke_check
run_first_preview
contact sheet
trace_preview_variant
adjust_pipeline
compare_preview_runs
export_pipeline
Explicit fallback:
run_host_smoke_check
preview_request_template
Do not render anything until validate_preview_request returns valid=true.
render_preview_batch
contact sheet
trace_preview_variant
adjust_pipeline
compare_preview_runs
export_pipeline
docs/assets/demo/demo_report.md
"""


def _workflow_text(document_name: str) -> str:
    return _valid_guide_text() if document_name == "guide" else _valid_prompt_text()


def _workflow_check(tmp_path: Path, *, document_name: str, text: str) -> FirstTenMinutesCheck:
    guide_text = text if document_name == "guide" else _valid_guide_text()
    prompt_text = text if document_name == "prompt" else _valid_prompt_text()
    report = check_first_10_minutes(_valid_config(tmp_path, guide_text=guide_text, prompt_text=prompt_text))
    check_name = "quickstart_guide" if document_name == "guide" else "host_prompt"
    return report.by_name[check_name]


def _valid_config(tmp_path: Path, *, guide_text: str, prompt_text: str) -> FirstTenMinutesConfig:
    readme = _write_text(
        tmp_path / "README.md",
        (
            "[guide](docs/FIRST_10_MINUTES.md)\n"
            "The guided run_first_preview workflow requires the default full or dataset capability profile.\n"
        ),
    )
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
