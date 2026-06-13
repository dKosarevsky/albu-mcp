import pytest

from albumentationsx_mcp.recipes import list_recipe_catalog, recommend_recipe


@pytest.mark.parametrize(
    ("task", "expected_profile", "expected_targets", "expected_transform"),
    [
        ("ocr", "ocr", ["image"], "Perspective"),
        ("object_detection", "detection", ["image", "bboxes"], "Affine"),
        ("segmentation", "segmentation", ["image", "mask"], "GaussNoise"),
        ("classification", "classification", ["image"], "MotionBlur"),
        ("unknown robustness task", "balanced", ["image"], "GaussNoise"),
    ],
)
def test_recommend_recipe_returns_task_aware_workflow(
    task: str,
    expected_profile: str,
    expected_targets: list[str],
    expected_transform: str,
) -> None:
    recipe = recommend_recipe(task, intensity="medium")

    assert recipe.task == task
    assert recipe.quality_profile == expected_profile
    assert recipe.targets == expected_targets
    assert expected_transform in [transform.name for transform in recipe.pipeline.transforms]
    assert "render_preview_batch" in recipe.recommended_tools
    assert "rank_preview_candidates" in recipe.recommended_tools
    assert "score_dataset_preview_candidates" in recipe.recommended_tools
    assert "export_preview_report" in recipe.recommended_tools
    assert recipe.feedback_tags
    assert recipe.rationale


def test_recommend_recipe_respects_explicit_targets() -> None:
    recipe = recommend_recipe("detection", intensity="low", targets=["image", "bboxes", "keypoints"])

    assert recipe.quality_profile == "detection"
    assert recipe.targets == ["image", "bboxes", "keypoints"]
    assert recipe.pipeline.bbox_params == {"format": "pascal_voc", "label_fields": ["labels"]}
    assert recipe.pipeline.keypoint_params == {"format": "xy", "remove_invisible": False}


def test_list_recipe_catalog_is_agent_legible_and_deterministic() -> None:
    catalog = list_recipe_catalog()

    assert [recipe.name for recipe in catalog] == [
        "classification",
        "detection",
        "segmentation",
        "ocr",
        "balanced",
    ]
    assert catalog[1].quality_profile == "detection"
    assert "object_detection" in catalog[1].task_aliases
    assert "too_distorted" in catalog[1].feedback_tags
