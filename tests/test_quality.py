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


def test_collect_image_quality_metrics_reports_color_entropy_and_clipping(tmp_path: Path) -> None:
    colorful_path = tmp_path / "colorful.png"
    clipped_path = tmp_path / "clipped.png"

    colorful = np.zeros((32, 32, 3), dtype=np.uint8)
    colorful[:16, :16] = [255, 0, 0]
    colorful[:16, 16:] = [0, 255, 0]
    colorful[16:, :16] = [0, 0, 255]
    colorful[16:, 16:] = [255, 255, 0]
    Image.fromarray(colorful).save(colorful_path)

    clipped = np.zeros((32, 32, 3), dtype=np.uint8)
    clipped[:, 16:] = 255
    Image.fromarray(clipped).save(clipped_path)

    colorful_metrics = collect_image_quality_metrics(colorful_path)
    clipped_metrics = collect_image_quality_metrics(clipped_path)

    assert colorful_metrics.saturation_mean > 180
    assert colorful_metrics.colorfulness_score > 180
    assert colorful_metrics.entropy_bits > 1.5
    assert clipped_metrics.clipping_fraction == 1.0


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


def test_compare_manifest_quality_reports_deterministic_findings(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.png"
    candidate_path = tmp_path / "candidate.png"
    Image.fromarray(np.full((32, 32, 3), 128, dtype=np.uint8)).save(baseline_path)
    Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8)).save(candidate_path)

    quality_summary, warnings = compare_manifest_quality(
        _manifest_with_images([baseline_path]),
        _manifest_with_images([candidate_path]),
    )

    assert warnings == []
    assert quality_summary is not None
    assert {finding.code for finding in quality_summary.findings} >= {
        "candidate_too_dark",
        "candidate_high_clipping",
    }
    clipping = next(finding for finding in quality_summary.findings if finding.code == "candidate_high_clipping")
    assert clipping.severity == "high"
    assert clipping.metric == "clipping_fraction"


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
