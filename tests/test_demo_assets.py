import json
from pathlib import Path

from scripts.check_demo_assets import check_demo_assets
from scripts.render_demo_assets import render_demo_assets


def test_demo_asset_generator_writes_reviewable_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "demo"

    manifest_path = render_demo_assets(output_dir)

    assert (output_dir / "inputs" / "sample-grid.png").exists()
    assert (output_dir / "contact_sheet.png").exists()
    assert (output_dir / "comparison_contact_sheet.png").exists()
    assert (output_dir / "demo_report.md").exists()
    assert manifest_path == output_dir / "demo_manifest.json"
    manifest = manifest_path.read_text(encoding="utf-8")
    assert "baseline_pipeline" in manifest
    assert "candidate_pipeline" in manifest
    assert "compare_preview_runs" in manifest
    assert json.loads(manifest)["input"] == "inputs/sample-grid.png"
    report = (output_dir / "demo_report.md").read_text(encoding="utf-8")
    assert "![Baseline contact sheet](contact_sheet.png)" in report
    assert "![Comparison contact sheet](comparison_contact_sheet.png)" in report
    assert "`too_noisy`" in report
    assert "Candidate accepted" in report


def test_demo_asset_guard_validates_generated_bundle(tmp_path: Path) -> None:
    report = check_demo_assets(tmp_path / "demo")

    assert report.ok is True
    assert report.manifest_path == tmp_path / "demo" / "demo_manifest.json"
    assert set(report.files) == {
        "inputs/sample-grid.png",
        "contact_sheet.png",
        "comparison_contact_sheet.png",
        "demo_report.md",
        "demo_manifest.json",
    }


def test_demo_asset_guard_rejects_stale_committed_bundle(tmp_path: Path) -> None:
    output_dir = tmp_path / "demo"
    render_demo_assets(output_dir)
    (output_dir / "demo_report.md").write_text("# stale\n", encoding="utf-8")

    report = check_demo_assets(output_dir, check_fresh=True)

    assert report.ok is False
    assert "stale files: demo_report.md" in report.message
