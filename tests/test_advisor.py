from dataclasses import dataclass

from albumentationsx_mcp.advisor import explain_pipeline, list_feedback_tags
from albumentationsx_mcp.models import ComposeSpec, TargetSpec, TransformMetadata, TransformSpec


@dataclass
class FakeCatalog:
    metadata: TransformMetadata

    def get_transform_schema(self, name: str) -> TransformMetadata:
        assert name == self.metadata.name
        return self.metadata


def test_list_feedback_tags_documents_adjustment_contract() -> None:
    tags = {tag.name: tag for tag in list_feedback_tags()}

    assert {"too_noisy", "too_blurry", "too_distorted", "object_unrecognizable"}.issubset(tags)
    assert tags["too_noisy"].description
    assert "noise" in tags["too_noisy"].applies_to


def test_explain_pipeline_flags_high_noise_and_suggests_feedback_tag() -> None:
    pipeline = ComposeSpec(
        transforms=[
            TransformSpec(name="HorizontalFlip", p=0.4),
            TransformSpec(name="GaussNoise", params={"std_range": (0.2, 0.6)}, p=0.9),
        ],
    )

    explanation = explain_pipeline(pipeline, TargetSpec(targets=["image"]))

    assert explanation.risk_level == "high"
    assert "too_noisy" in explanation.suggested_feedback_tags
    assert any(warning.code == "high_noise" for warning in explanation.warnings)
    assert any(item.name == "GaussNoise" and item.category == "noise" for item in explanation.transforms)


def test_explain_pipeline_flags_strong_geometric_distortion() -> None:
    pipeline = ComposeSpec(
        transforms=[
            TransformSpec(name="Perspective", params={"scale": (0.08, 0.16)}, p=0.85),
        ],
    )

    explanation = explain_pipeline(pipeline, TargetSpec(targets=["image", "bboxes"], bbox_type="hbb"))

    assert explanation.risk_level == "high"
    assert "too_distorted" in explanation.suggested_feedback_tags
    assert any(warning.code == "high_geometric_distortion" for warning in explanation.warnings)


def test_explain_pipeline_uses_catalog_metadata_for_target_support() -> None:
    catalog = FakeCatalog(
        TransformMetadata(
            name="ImageOnlyCustom",
            module="custom.transforms",
            transform_type="image_only",
            targets=["image"],
            docstring_short="Applies image-only color noise.",
        ),
    )
    pipeline = ComposeSpec(transforms=[TransformSpec(name="ImageOnlyCustom", p=0.5)])

    explanation = explain_pipeline(pipeline, TargetSpec(targets=["image", "bboxes"]), catalog=catalog)

    transform = explanation.transforms[0]
    assert transform.transform_type == "image_only"
    assert transform.targets == ["image"]
    assert transform.metadata_summary == "Applies image-only color noise."
    assert any(warning.code == "target_not_supported_by_transform" for warning in explanation.warnings)
