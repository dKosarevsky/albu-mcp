from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from albumentationsx_mcp.quality import collect_image_quality_metrics, compare_manifest_quality


def test_collect_image_quality_metrics_detects_contrast_and_sharpness(tmp_path: Path) -> None:
    flat_path = tmp_path / "flat.png"
    striped_path = tmp_path / "striped.png"
    blurred_path = tmp_path / "blurred.png"
    Image.fromarray(np.full((32, 32, 3), 128, dtype=np.uint8)).save(flat_path)
    striped = np.zeros((32, 32, 3), dtype=np.uint8)
    striped[:, ::2] = 255
    Image.fromarray(striped).save(striped_path)
    Image.fromarray(striped).filter(ImageFilter.GaussianBlur(radius=2)).save(blurred_path)

    flat_metrics = collect_image_quality_metrics(flat_path)
    striped_metrics = collect_image_quality_metrics(striped_path)
    blurred_metrics = collect_image_quality_metrics(blurred_path)

    assert striped_metrics.contrast_std > flat_metrics.contrast_std
    assert striped_metrics.sharpness_score > blurred_metrics.sharpness_score


def test_compare_manifest_quality_reports_deltas(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.png"
    candidate_path = tmp_path / "candidate.png"
    Image.fromarray(np.full((16, 16, 3), 80, dtype=np.uint8)).save(baseline_path)
    Image.fromarray(np.full((16, 16, 3), 140, dtype=np.uint8)).save(candidate_path)

    quality_summary, warnings = compare_manifest_quality(
        _manifest_with_images([baseline_path]),
        _manifest_with_images([candidate_path]),
    )

    assert warnings == []
    assert quality_summary is not None
    assert quality_summary.baseline.image_count == 1
    assert quality_summary.candidate.image_count == 1
    assert quality_summary.deltas["brightness_mean"] == 60.0


def _manifest_with_images(paths: list[Path]) -> dict:
    return {
        "artifacts": [
            {
                "kind": "image",
                "path": str(path),
            }
            for path in paths
        ],
    }
