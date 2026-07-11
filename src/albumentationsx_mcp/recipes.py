"""Task-aware recipe recommendations for preview tuning workflows."""

from __future__ import annotations

from typing import NamedTuple

from albumentationsx_mcp.models import QualityProfileName, RecipeExplanation, RecipeInfo, RecipeRecommendation
from albumentationsx_mcp.presets import Intensity
from albumentationsx_mcp.presets import recommend_pipeline as recommend_preset_pipeline

_RECOMMENDED_TOOLS = [
    "render_preview_batch",
    "rank_preview_candidates",
    "score_dataset_preview_candidates",
    "start_tuning_session",
    "record_tuning_session_step",
    "export_tuning_session",
    "export_preview_report",
    "record_tuning_decision",
    "export_pipeline",
]
_COMMON_FEEDBACK_TAGS = [
    "too_noisy",
    "too_blurry",
    "too_distorted",
    "exposure_too_weak",
    "object_unrecognizable",
]


class RecipeDefinition(NamedTuple):
    """Internal immutable recipe definition."""

    name: str
    description: str
    task_aliases: tuple[str, ...]
    quality_profile: QualityProfileName
    default_targets: tuple[str, ...]
    feedback_tags: tuple[str, ...]
    preset_task: str


_RECIPES: tuple[RecipeDefinition, ...] = (
    RecipeDefinition(
        name="classification",
        description="General classification robustness recipe that keeps images recognizable.",
        task_aliases=("classification", "image_classification", "classifier"),
        quality_profile="classification",
        default_targets=("image",),
        feedback_tags=("too_noisy", "too_blurry", "exposure_too_weak", "object_unrecognizable"),
        preset_task="classification",
    ),
    RecipeDefinition(
        name="detection",
        description="Object detection recipe with bbox-aware quality review.",
        task_aliases=("detection", "object_detection", "bboxes", "bbox"),
        quality_profile="detection",
        default_targets=("image", "bboxes"),
        feedback_tags=("too_distorted", "exposure_too_weak", "object_unrecognizable"),
        preset_task="object_detection",
    ),
    RecipeDefinition(
        name="segmentation",
        description="Segmentation recipe that prioritizes mask coverage retention.",
        task_aliases=("segmentation", "semantic_segmentation", "instance_segmentation", "mask"),
        quality_profile="segmentation",
        default_targets=("image", "mask"),
        feedback_tags=("too_distorted", "too_noisy", "exposure_too_weak", "object_unrecognizable"),
        preset_task="segmentation",
    ),
    RecipeDefinition(
        name="ocr",
        description="OCR and document recipe focused on legibility under mild distortion.",
        task_aliases=("ocr", "document", "document_distortion", "text_recognition"),
        quality_profile="ocr",
        default_targets=("image",),
        feedback_tags=("too_blurry", "too_distorted", "object_unrecognizable"),
        preset_task="ocr",
    ),
    RecipeDefinition(
        name="balanced",
        description="Fallback image robustness recipe for unspecified computer vision tasks.",
        task_aliases=("balanced", "general", "robustness", "augmentation"),
        quality_profile="balanced",
        default_targets=("image",),
        feedback_tags=tuple(_COMMON_FEEDBACK_TAGS),
        preset_task="general",
    ),
)


def list_recipe_catalog() -> list[RecipeInfo]:
    """Return deterministic task recipe metadata for MCP resources."""
    return [_recipe_info(recipe) for recipe in _RECIPES]


def recommend_recipe(
    task: str,
    *,
    intensity: Intensity = "medium",
    targets: list[str] | None = None,
) -> RecipeRecommendation:
    """Recommend a task-aware starter pipeline and workflow envelope."""
    recipe = _match_recipe(task)
    selected_targets = list(targets) if targets is not None else list(recipe.default_targets)
    pipeline = recommend_preset_pipeline(recipe.preset_task, intensity=intensity, targets=selected_targets)
    explanations = _explanations(recipe, task=task, targets=selected_targets, explicit_targets=targets is not None)
    return RecipeRecommendation(
        task=task,
        recipe_name=recipe.name,
        intensity=intensity,
        targets=selected_targets,
        quality_profile=recipe.quality_profile,
        pipeline=pipeline,
        recommended_tools=list(_RECOMMENDED_TOOLS),
        feedback_tags=list(recipe.feedback_tags),
        preview_guidance=_preview_guidance(recipe),
        explanations=explanations,
        rationale=_rationale(recipe),
    )


def _recipe_info(recipe: RecipeDefinition) -> RecipeInfo:
    return RecipeInfo(
        name=recipe.name,
        description=recipe.description,
        task_aliases=list(recipe.task_aliases),
        quality_profile=recipe.quality_profile,
        default_targets=list(recipe.default_targets),
        feedback_tags=list(recipe.feedback_tags),
        recommended_tools=list(_RECOMMENDED_TOOLS),
    )


def _match_recipe(task: str) -> RecipeDefinition:
    normalized = _normalize_task(task)
    for recipe in _RECIPES:
        if normalized in recipe.task_aliases:
            return recipe
    return _RECIPES[-1]


def _explanations(
    recipe: RecipeDefinition,
    *,
    task: str,
    targets: list[str],
    explicit_targets: bool,
) -> list[RecipeExplanation]:
    return [
        RecipeExplanation(
            kind="quality_profile",
            selected=recipe.quality_profile,
            rationale=_quality_profile_rationale(recipe, task),
        ),
        RecipeExplanation(
            kind="targets",
            selected=targets,
            rationale=_targets_rationale(recipe, explicit_targets=explicit_targets),
        ),
        RecipeExplanation(
            kind="feedback_tags",
            selected=list(recipe.feedback_tags),
            rationale="These feedback tags match the transforms and failure modes most likely to matter for this task.",
        ),
        RecipeExplanation(
            kind="workflow",
            selected=list(_RECOMMENDED_TOOLS),
            rationale="Render, rank, score, report, record the decision, then export only after preview acceptance.",
        ),
    ]


def _quality_profile_rationale(recipe: RecipeDefinition, task: str) -> str:
    normalized = _normalize_task(task)
    if recipe.name == "balanced" and normalized not in recipe.task_aliases:
        return "Used the balanced fallback because the task did not match a specialized recipe alias."
    return f"Selected the {recipe.quality_profile} quality profile for the matched {recipe.name} recipe."


def _targets_rationale(recipe: RecipeDefinition, *, explicit_targets: bool) -> str:
    if explicit_targets:
        return "Used explicit targets supplied by the host so validation and preview rendering match the dataset."
    return f"Used default targets for the {recipe.name} recipe."


def _normalize_task(task: str) -> str:
    return task.strip().lower().replace("-", "_").replace(" ", "_")


def _preview_guidance(recipe: RecipeDefinition) -> list[str]:
    return [
        f"Use the {recipe.quality_profile} quality profile when comparing preview runs.",
        "Render at least two candidate preview runs before ranking.",
        "Score the candidate set before exporting a report or final pipeline.",
    ]


def _rationale(recipe: RecipeDefinition) -> str:
    return (
        f"Matched the {recipe.name} recipe, selected the {recipe.quality_profile} quality profile, "
        "and paired a conservative starter pipeline with preview ranking and report export tools."
    )
