from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from albumentationsx_mcp.quality import collect_image_quality_metrics, compare_manifest_quality, list_quality_profiles


def test_list_quality_profiles_documents_task_thresholds() -> None:
    profiles = {profile.name: profile for profile in list_quality_profiles()}

    assert {"balanced", "classification", "detection", "segmentation", "ocr"}.issubset(profiles)
    assert profiles["balanced"].description
    assert profiles["ocr"].thresholds["entropy_bits_medium"] > profiles["balanced"].thresholds["entropy_bits_medium"]
    assert profiles["detection"].thresholds["bbox_retention_high"] == 1.0
    assert profiles["segmentation"].thresholds["mask_coverage_medium"] > profiles["balanced"].thresholds[
        "mask_coverage_medium"
    ]


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


def test_compare_manifest_quality_summarizes_annotation_retention() -> None:
    quality_summary, warnings = compare_manifest_quality(
        _manifest_with_annotation_observations(
            [
                {
                    "input_bbox_count": 2,
                    "output_bbox_count": 2,
                    "input_keypoint_count": 1,
                    "output_keypoint_count": 1,
                    "input_mask_coverage": 0.25,
                    "output_mask_coverage": 0.25,
                }
            ]
        ),
        _manifest_with_annotation_observations(
            [
                {
                    "input_bbox_count": 2,
                    "output_bbox_count": 1,
                    "input_keypoint_count": 1,
                    "output_keypoint_count": 0,
                    "input_mask_coverage": 0.25,
                    "output_mask_coverage": 0.1,
                }
            ]
        ),
    )

    assert warnings == []
    assert quality_summary is not None
    assert quality_summary.annotation_summary is not None
    assert quality_summary.annotation_summary.baseline.bbox_retention_ratio == 1.0
    assert quality_summary.annotation_summary.candidate.bbox_retention_ratio == 0.5
    assert quality_summary.annotation_summary.deltas["bbox_retention_ratio"] == -0.5
    assert {finding.code for finding in quality_summary.findings} >= {
        "candidate_bbox_loss",
        "candidate_keypoint_loss",
        "candidate_mask_coverage_drop",
    }


def test_compare_manifest_quality_ocr_profile_is_stricter_about_low_entropy(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.png"
    candidate_path = tmp_path / "candidate.png"
    baseline = np.zeros((32, 32, 3), dtype=np.uint8)
    baseline[:16, :16] = 64
    baseline[:16, 16:] = 96
    baseline[16:, :16] = 128
    baseline[16:, 16:] = 160
    candidate = np.full((32, 32, 3), 96, dtype=np.uint8)
    candidate[:, 16:] = 128
    Image.fromarray(baseline).save(baseline_path)
    Image.fromarray(candidate).save(candidate_path)

    balanced_summary, _ = compare_manifest_quality(
        _manifest_with_images([baseline_path]),
        _manifest_with_images([candidate_path]),
    )
    ocr_summary, _ = compare_manifest_quality(
        _manifest_with_images([baseline_path]),
        _manifest_with_images([candidate_path]),
        quality_profile="ocr",
    )

    assert balanced_summary is not None
    assert ocr_summary is not None
    assert "candidate_low_entropy" not in {finding.code for finding in balanced_summary.findings}
    assert "candidate_low_entropy" in {finding.code for finding in ocr_summary.findings}
    assert ocr_summary.quality_profile == "ocr"


def test_compare_manifest_quality_detection_profile_marks_bbox_loss_high() -> None:
    quality_summary, _ = compare_manifest_quality(
        _manifest_with_annotation_observations(
            [
                {
                    "input_bbox_count": 2,
                    "output_bbox_count": 2,
                }
            ]
        ),
        _manifest_with_annotation_observations(
            [
                {
                    "input_bbox_count": 2,
                    "output_bbox_count": 1,
                }
            ]
        ),
        quality_profile="detection",
    )

    assert quality_summary is not None
    bbox_loss = next(finding for finding in quality_summary.findings if finding.code == "candidate_bbox_loss")
    assert bbox_loss.severity == "high"


def test_compare_manifest_quality_segmentation_profile_flags_smaller_mask_drop() -> None:
    balanced_summary, _ = compare_manifest_quality(
        _manifest_with_annotation_observations(
            [
                {
                    "input_mask_coverage": 0.25,
                    "output_mask_coverage": 0.25,
                }
            ]
        ),
        _manifest_with_annotation_observations(
            [
                {
                    "input_mask_coverage": 0.25,
                    "output_mask_coverage": 0.2,
                }
            ]
        ),
    )
    segmentation_summary, _ = compare_manifest_quality(
        _manifest_with_annotation_observations(
            [
                {
                    "input_mask_coverage": 0.25,
                    "output_mask_coverage": 0.25,
                }
            ]
        ),
        _manifest_with_annotation_observations(
            [
                {
                    "input_mask_coverage": 0.25,
                    "output_mask_coverage": 0.2,
                }
            ]
        ),
        quality_profile="segmentation",
    )

    assert balanced_summary is not None
    assert segmentation_summary is not None
    assert "candidate_mask_coverage_drop" not in {finding.code for finding in balanced_summary.findings}
    assert "candidate_mask_coverage_drop" in {finding.code for finding in segmentation_summary.findings}


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


def _manifest_with_annotation_observations(observations: list[dict]) -> dict:
    return {
        "annotation_observations": [
            {
                "image_index": index,
                "variant_index": 0,
                **observation,
            }
            for index, observation in enumerate(observations)
        ],
    }
