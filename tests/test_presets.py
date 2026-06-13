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


def test_classification_recommendation_uses_current_motion_blur_parameter_name() -> None:
    spec = recommend_pipeline(task="classification", intensity="medium", targets=["image"])
    motion_blur = next(transform for transform in spec.transforms if transform.name == "MotionBlur")

    assert "blur_range" in motion_blur.params
    assert "blur_limit" not in motion_blur.params
