import pytest

from albumentationsx_mcp.models import ComposeSpec, TransformSpec
from albumentationsx_mcp.presets import adjust_pipeline, recommend_pipeline


def test_detection_recommendation_includes_bbox_params() -> None:
    spec = recommend_pipeline(task="object_detection", intensity="medium", targets=["image", "bboxes"])

    assert spec.bbox_params is not None
    assert spec.bbox_params["format"] == "pascal_voc"
    assert any(transform.name == "Affine" for transform in spec.transforms)


def test_adjust_pipeline_reduces_noise_when_feedback_says_too_noisy() -> None:
    spec = ComposeSpec(transforms=[TransformSpec(name="GaussNoise", params={"std_range": (0.1, 0.4)}, p=0.8)])

    adjusted = adjust_pipeline(spec, feedback_tags=["too_noisy"])

    transform = adjusted.transforms[0]
    assert transform.p == 0.4
    assert transform.params["std_range"] == (0.05, 0.2)


@pytest.mark.parametrize(
    ("feedback_tag", "expected_probability", "expected_range"),
    [
        ("too_noisy:low", 0.6, (0.075, 0.3)),
        ("too_noisy:medium", 0.4, (0.05, 0.2)),
        ("too_noisy:high", 0.2, (0.025, 0.1)),
    ],
)
def test_adjust_pipeline_scales_feedback_by_severity(
    feedback_tag: str,
    expected_probability: float,
    expected_range: tuple[float, float],
) -> None:
    spec = ComposeSpec(transforms=[TransformSpec(name="GaussNoise", params={"std_range": (0.1, 0.4)}, p=0.8)])

    adjusted = adjust_pipeline(spec, feedback_tags=[feedback_tag])

    transform = adjusted.transforms[0]
    assert transform.p == expected_probability
    assert transform.params["std_range"] == expected_range


def test_adjust_pipeline_uses_strongest_duplicate_feedback_severity() -> None:
    spec = ComposeSpec(transforms=[TransformSpec(name="GaussNoise", params={"std_range": (0.1, 0.4)}, p=0.8)])

    adjusted = adjust_pipeline(spec, feedback_tags=["too_noisy:low", "too_noisy:high"])

    transform = adjusted.transforms[0]
    assert transform.p == 0.2
    assert transform.params["std_range"] == (0.025, 0.1)


def test_adjust_pipeline_reduces_color_transforms_from_exposure_feedback() -> None:
    spec = ComposeSpec(
        transforms=[
            TransformSpec(
                name="RandomBrightnessContrast",
                params={"brightness_limit": (-0.4, 0.4), "contrast_limit": (-0.2, 0.2)},
                p=0.8,
            ),
            TransformSpec(name="HueSaturationValue", params={"hue_shift_limit": (-20, 20)}, p=0.6),
        ]
    )

    adjusted = adjust_pipeline(spec, feedback_tags=["too_bright:high", "color_shift:medium"])

    brightness = adjusted.transforms[0]
    hue = adjusted.transforms[1]
    assert brightness.p == 0.24
    assert brightness.params["brightness_limit"] == (-0.12, 0.12)
    assert hue.p == 0.3
    assert hue.params["hue_shift_limit"] == (-10, 10)


def test_classification_recommendation_uses_current_motion_blur_parameter_name() -> None:
    spec = recommend_pipeline(task="classification", intensity="medium", targets=["image"])
    motion_blur = next(transform for transform in spec.transforms if transform.name == "MotionBlur")

    assert "blur_range" in motion_blur.params
    assert "blur_limit" not in motion_blur.params
