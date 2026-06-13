from pathlib import Path

from scripts.render_demo_assets import render_demo_assets


def test_demo_asset_generator_writes_reviewable_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "demo"

    manifest_path = render_demo_assets(output_dir)

    assert (output_dir / "inputs" / "sample-grid.png").exists()
    assert (output_dir / "contact_sheet.png").exists()
    assert (output_dir / "comparison_contact_sheet.png").exists()
    assert manifest_path == output_dir / "demo_manifest.json"
    manifest = manifest_path.read_text(encoding="utf-8")
    assert "baseline_pipeline" in manifest
    assert "candidate_pipeline" in manifest
    assert "compare_preview_runs" in manifest
