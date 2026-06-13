"""Structured preview feedback helpers shared by adjustment and comparison."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, cast

FeedbackSeverity = Literal["low", "medium", "high"]

_DEFAULT_SEVERITY: FeedbackSeverity = "medium"
_SEVERITY_ORDER: dict[FeedbackSeverity, int] = {"low": 0, "medium": 1, "high": 2}
_SEVERITY_MULTIPLIER: dict[FeedbackSeverity, float] = {"low": 1.5, "medium": 1.0, "high": 0.5}
_MAX_REDUCTION_FACTOR = 0.95
_TAG_PRIORITY = ["too_noisy", "too_blurry", "too_distorted", "object_unrecognizable"]
_TRANSFORM_FEEDBACK_RULES = [
    (("noise",), ("too_noisy",)),
    (("blur",), ("too_blurry",)),
    (("affine", "perspective", "distortion", "elastic", "grid", "rotate"), ("too_distorted",)),
    (("compression", "jpeg", "dropout", "erase", "coarse"), ("object_unrecognizable",)),
]


def normalize_feedback_tags(feedback_tags: Iterable[str]) -> dict[str, FeedbackSeverity]:
    """Parse feedback tags and keep the strongest severity for each base tag."""
    normalized: dict[str, FeedbackSeverity] = {}
    for raw_tag in feedback_tags:
        base_tag, severity = _parse_feedback_tag(raw_tag)
        if not base_tag:
            continue
        current = normalized.get(base_tag)
        if current is None or _SEVERITY_ORDER[severity] > _SEVERITY_ORDER[current]:
            normalized[base_tag] = severity
    return normalized


def severity_scaled_factor(base_factor: float, severity: FeedbackSeverity) -> float:
    """Return a reduction factor adjusted by feedback severity."""
    return round(min(_MAX_REDUCTION_FACTOR, max(0.0, base_factor * _SEVERITY_MULTIPLIER[severity])), 6)


def suggested_feedback_tags_for_transform_names(
    candidate_transform_names: Iterable[str],
    baseline_transform_names: Iterable[str] = (),
) -> list[str]:
    """Suggest feedback tags to consider for candidate transforms."""
    baseline_names = {name.lower() for name in baseline_transform_names}
    candidate_names = list(candidate_transform_names)
    changed_names = [name for name in candidate_names if name.lower() not in baseline_names]
    suggested_tags = _tags_for_transform_names(changed_names)
    if not suggested_tags:
        suggested_tags = _tags_for_transform_names(candidate_names)
    return [tag for tag in _TAG_PRIORITY if tag in suggested_tags]


def _parse_feedback_tag(raw_tag: str) -> tuple[str, FeedbackSeverity]:
    base_tag, separator, raw_severity = raw_tag.strip().lower().partition(":")
    if not separator:
        return base_tag, _DEFAULT_SEVERITY
    severity = raw_severity.strip()
    if severity in _SEVERITY_ORDER:
        return base_tag, cast("FeedbackSeverity", severity)
    return base_tag, _DEFAULT_SEVERITY


def _tags_for_transform_names(transform_names: Iterable[str]) -> set[str]:
    tags: set[str] = set()
    for transform_name in transform_names:
        lowered = transform_name.lower()
        for tokens, feedback_tags in _TRANSFORM_FEEDBACK_RULES:
            if any(token in lowered for token in tokens):
                tags.update(feedback_tags)
    return tags
