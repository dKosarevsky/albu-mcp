"""Transport-independent MCP capability profile values."""

from __future__ import annotations

from enum import Enum


class CapabilityProfile(str, Enum):
    """One opt-in view of the canonical MCP surface."""

    CORE = "core"
    REVIEW = "review"
    DATASET = "dataset"
    FULL = "full"

    def __str__(self) -> str:
        """Return the stable configuration value."""
        return self.value


CAPABILITY_PROFILES = tuple(CapabilityProfile)
CAPABILITY_PROFILE_VALUES = tuple(profile.value for profile in CAPABILITY_PROFILES)
CORE_PROFILE_MEMBERSHIP = (
    CapabilityProfile.CORE,
    CapabilityProfile.REVIEW,
    CapabilityProfile.DATASET,
    CapabilityProfile.FULL,
)
REVIEW_PROFILE_MEMBERSHIP = (
    CapabilityProfile.REVIEW,
    CapabilityProfile.FULL,
)
DATASET_PROFILE_MEMBERSHIP = (
    CapabilityProfile.DATASET,
    CapabilityProfile.FULL,
)
FULL_PROFILE_MEMBERSHIP = (CapabilityProfile.FULL,)


def parse_capability_profile(value: str | CapabilityProfile) -> CapabilityProfile:
    """Parse one profile value with a stable accepted-values error."""
    if isinstance(value, CapabilityProfile):
        return value
    try:
        return CapabilityProfile(value)
    except ValueError as exc:
        accepted = ", ".join(CAPABILITY_PROFILE_VALUES)
        msg = f"unknown capability profile {value!r}; expected one of: {accepted}"
        raise ValueError(msg) from exc
