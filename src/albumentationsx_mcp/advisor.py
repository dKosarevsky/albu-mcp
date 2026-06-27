"""Pipeline explanation and feedback tag contracts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from albumentationsx_mcp.models import (
    ComposeSpec,
    FeedbackTagInfo,
    PipelineExplanation,
    RiskLevel,
    TargetSpec,
    TransformExplanation,
    TransformMetadata,
    TransformSpec,
    ValidationIssue,
)

_HIGH_PROBABILITY = 0.75
_DESTRUCTIVE_PROBABILITY = 0.7
_COMPRESSION_OCCLUSION_PROBABILITY = 0.65
_NOISE_STRENGTH = 0.3
_BLUR_STRENGTH = 7.0
_PERSPECTIVE_SCALE = 0.08
_ROTATE_DEGREES = 15.0
_GEOMETRIC_PROBABILITY = 0.8
_GEOMETRIC_STRENGTH = 0.05
_HIGH_RISK_POINTS = 4
_MEDIUM_RISK_POINTS = 2

_CATEGORY_RULES = [
    (("noise",), "noise"),
    (("blur",), "blur"),
    (("affine", "perspective", "distortion", "elastic", "grid"), "geometric"),
    (("brightness", "contrast", "color", "hue", "saturation", "rgb", "gray"), "color"),
    (("compression", "jpeg"), "compression"),
    (("dropout", "erase", "coarse"), "occlusion"),
    (("flip", "rotate", "crop", "resize"), "geometric"),
]

_FEEDBACK_TAGS = [
    FeedbackTagInfo(
        name="too_noisy",
        description="Noise makes objects, text, or boundaries harder to recognize.",
        applies_to=["noise"],
        mitigation="Reduce noise probabilities and numeric noise ranges; append :low, :medium, or :high for severity.",
    ),
    FeedbackTagInfo(
        name="too_blurry",
        description="Blur removes details that should stay visible for the task.",
        applies_to=["blur"],
        mitigation="Reduce blur probabilities and kernel or sigma ranges; append :low, :medium, or :high for severity.",
    ),
    FeedbackTagInfo(
        name="too_distorted",
        description="Geometric transforms bend, rotate, or warp samples beyond realistic variation.",
        applies_to=["geometric"],
        mitigation=(
            "Reduce affine, perspective, and distortion probabilities and ranges; "
            "append :low, :medium, or :high for severity."
        ),
    ),
    FeedbackTagInfo(
        name="too_dark",
        description="Exposure changes make objects, text, or boundaries too dark to inspect.",
        applies_to=["color"],
        mitigation=(
            "Reduce brightness and contrast transform probabilities and ranges; "
            "append :low, :medium, or :high for severity."
        ),
    ),
    FeedbackTagInfo(
        name="too_bright",
        description="Exposure changes wash out or overexpose task evidence.",
        applies_to=["color"],
        mitigation=(
            "Reduce brightness and contrast transform probabilities and ranges; "
            "append :low, :medium, or :high for severity."
        ),
    ),
    FeedbackTagInfo(
        name="color_shift",
        description="Hue, saturation, RGB, or color jitter changes make samples look unrealistic.",
        applies_to=["color"],
        mitigation=(
            "Reduce hue, saturation, RGB shift, and color jitter probabilities and ranges; "
            "append :low, :medium, or :high for severity."
        ),
    ),
    FeedbackTagInfo(
        name="object_unrecognizable",
        description="The augmented sample no longer preserves the labeled object or class evidence.",
        applies_to=["noise", "blur", "compression", "occlusion", "geometric"],
        mitigation=(
            "Globally reduce destructive transform probabilities and ranges; "
            "append :low, :medium, or :high for severity."
        ),
    ),
]


class MetadataCatalog(Protocol):
    """Catalog contract needed for metadata-aware explanations."""

    def get_transform_schema(self, name: str) -> TransformMetadata: ...


def list_feedback_tags() -> list[FeedbackTagInfo]:
    """Return the structured feedback tags understood by adjustment tools."""
    return list(_FEEDBACK_TAGS)


def explain_pipeline(
    pipeline: ComposeSpec,
    target: TargetSpec | None = None,
    *,
    catalog: MetadataCatalog | None = None,
) -> PipelineExplanation:
    """Explain likely augmentation effects and risks for an agent-guided preview session."""
    target = target or TargetSpec()
    transform_explanations: list[TransformExplanation] = []
    warnings: list[ValidationIssue] = []
    suggested_tags: set[str] = set()
    risk_points = 0

    for index, transform in enumerate(pipeline.transforms):
        metadata = _get_metadata(catalog, transform.name)
        category = _category_for_transform(transform.name, metadata)
        probability = 0.5 if transform.p is None else transform.p
        notable_params = _notable_params(transform)
        transform_explanations.append(
            TransformExplanation(
                name=transform.name,
                category=category,
                probability=probability,
                impact=_impact_for_category(category),
                transform_type=metadata.transform_type if metadata else None,
                targets=metadata.targets if metadata else [],
                metadata_summary=metadata.docstring_short if metadata else None,
                notable_params=notable_params,
            ),
        )

        if probability >= _HIGH_PROBABILITY:
            risk_points += 1
            warnings.append(
                ValidationIssue(
                    code="high_probability",
                    path=f"transforms.{index}.p",
                    message=f"{transform.name} runs with high probability {probability}.",
                ),
            )

        category_risk, category_warnings, category_tags = _category_risk(transform, category, probability, index)
        risk_points += category_risk
        warnings.extend(category_warnings)
        suggested_tags.update(category_tags)
        metadata_risk, metadata_warnings = _metadata_risk(transform, metadata, target, index)
        risk_points += metadata_risk
        warnings.extend(metadata_warnings)

        if category == "geometric" and any(item in target.targets for item in ["bboxes", "keypoints", "mask"]):
            risk_points += 1
            warnings.append(
                ValidationIssue(
                    code="annotation_alignment_sensitive",
                    path=f"transforms.{index}.name",
                    message=f"{transform.name} changes geometry and should be previewed with annotations.",
                ),
            )

    risk_level = _risk_level(risk_points)
    if risk_level == "high":
        suggested_tags.add("object_unrecognizable")

    return PipelineExplanation(
        risk_level=risk_level,
        summary=_summary(transform_explanations, risk_level),
        transforms=transform_explanations,
        warnings=warnings,
        suggested_feedback_tags=sorted(suggested_tags),
    )


def _category_risk(
    transform: TransformSpec,
    category: str,
    probability: float,
    index: int,
) -> tuple[int, list[ValidationIssue], set[str]]:
    max_numeric = max(_numeric_values(transform.params), default=0.0)
    warnings: list[ValidationIssue] = []
    tags: set[str] = set()
    risk_points = 0

    if category == "noise" and (probability >= _DESTRUCTIVE_PROBABILITY or max_numeric >= _NOISE_STRENGTH):
        risk_points += 3
        tags.add("too_noisy")
        warnings.append(_warning("high_noise", index, transform.name, "Noise strength may obscure task evidence."))
    elif category == "blur" and (probability >= _DESTRUCTIVE_PROBABILITY or max_numeric >= _BLUR_STRENGTH):
        risk_points += 2
        tags.add("too_blurry")
        warnings.append(_warning("high_blur", index, transform.name, "Blur strength may remove fine details."))
    elif category == "geometric" and _has_strong_geometry(transform, max_numeric, probability):
        risk_points += 3
        tags.add("too_distorted")
        warnings.append(
            _warning(
                "high_geometric_distortion",
                index,
                transform.name,
                "Geometric strength may move samples outside realistic variation.",
            ),
        )
    elif category in {"compression", "occlusion"} and probability >= _COMPRESSION_OCCLUSION_PROBABILITY:
        risk_points += 2
        tags.add("object_unrecognizable")
        warnings.append(
            _warning(
                f"high_{category}",
                index,
                transform.name,
                f"{category.title()} may remove visible task evidence.",
            ),
        )

    return risk_points, warnings, tags


def _warning(code: str, index: int, transform_name: str, message: str) -> ValidationIssue:
    return ValidationIssue(code=code, path=f"transforms.{index}.name", message=f"{transform_name}: {message}")


def _get_metadata(catalog: MetadataCatalog | None, name: str) -> TransformMetadata | None:
    if catalog is None:
        return None
    try:
        return catalog.get_transform_schema(name)
    except KeyError:
        return None


def _metadata_risk(
    transform: TransformSpec,
    metadata: TransformMetadata | None,
    target: TargetSpec,
    index: int,
) -> tuple[int, list[ValidationIssue]]:
    if metadata is None:
        return 0, []
    requested_annotation_targets = set(target.targets) - {"image", "images", "volume", "volumes"}
    if not requested_annotation_targets:
        return 0, []
    supported_targets = set(metadata.targets)
    unsupported_targets = sorted(requested_annotation_targets - supported_targets)
    if metadata.transform_type == "image_only":
        unsupported_targets = sorted(requested_annotation_targets)
    if not unsupported_targets:
        return 0, []
    return 1, [
        ValidationIssue(
            code="target_not_supported_by_transform",
            path=f"transforms.{index}.name",
            message=f"{transform.name} metadata does not advertise targets: {', '.join(unsupported_targets)}",
        ),
    ]


def _category_for_transform(name: str, metadata: TransformMetadata | None = None) -> str:
    lowered = " ".join(
        [
            name,
            metadata.module if metadata else "",
            metadata.docstring_short if metadata and metadata.docstring_short else "",
        ],
    ).lower()
    for tokens, category in _CATEGORY_RULES:
        if any(token in lowered for token in tokens):
            return category
    return "general"


def _impact_for_category(category: str) -> str:
    impacts = {
        "noise": "Adds sensor or pixel noise; useful for robustness but can hide small objects or text.",
        "blur": "Reduces high-frequency detail; useful for motion or focus variation.",
        "geometric": "Changes position, scale, orientation, or perspective.",
        "color": "Changes illumination or color response without moving annotations.",
        "compression": "Adds codec artifacts and detail loss.",
        "occlusion": "Removes or masks visual regions.",
        "general": "Applies general augmentation effects.",
    }
    return impacts[category]


def _notable_params(transform: TransformSpec) -> dict[str, Any]:
    return {
        key: value
        for key, value in transform.params.items()
        if any(token in key.lower() for token in ["range", "limit", "scale", "rotate", "quality", "sigma"])
    }


def _numeric_values(value: Any) -> Iterable[float]:
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [abs(float(value))]
    if isinstance(value, dict):
        values: list[float] = []
        for nested in value.values():
            values.extend(_numeric_values(nested))
        return values
    if isinstance(value, (list, tuple)):
        values = []
        for nested in value:
            values.extend(_numeric_values(nested))
        return values
    return []


def _has_strong_geometry(transform: TransformSpec, max_numeric: float, probability: float) -> bool:
    lowered_params = {key.lower(): value for key, value in transform.params.items()}
    if "scale" in lowered_params and max(_numeric_values(lowered_params["scale"]), default=0.0) >= _PERSPECTIVE_SCALE:
        return True
    if "rotate" in lowered_params and max(_numeric_values(lowered_params["rotate"]), default=0.0) >= _ROTATE_DEGREES:
        return True
    return probability >= _GEOMETRIC_PROBABILITY and max_numeric > _GEOMETRIC_STRENGTH


def _risk_level(points: int) -> RiskLevel:
    if points >= _HIGH_RISK_POINTS:
        return "high"
    if points >= _MEDIUM_RISK_POINTS:
        return "medium"
    return "low"


def _summary(transforms: list[TransformExplanation], risk_level: str) -> str:
    categories = sorted({transform.category for transform in transforms})
    return f"{len(transforms)} transforms across {', '.join(categories)} categories; preview risk is {risk_level}."
