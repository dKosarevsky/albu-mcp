"""Pure contracts for declared MCP adapter ownership."""

from __future__ import annotations

from dataclasses import dataclass, field

from albumentationsx_mcp.capabilities import CapabilityProfile


@dataclass(frozen=True, slots=True)
class ProfileSurface:
    """Identifiers exposed by one or more capability profiles."""

    profiles: tuple[CapabilityProfile, ...]
    tools: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    resource_templates: tuple[str, ...] = ()
    prompts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject empty, duplicate, or unknown profile values."""
        if not self.profiles:
            msg = "profile declaration must name at least one capability profile"
            raise ValueError(msg)
        if len(set(self.profiles)) != len(self.profiles):
            msg = "duplicate capability profile in profile declaration"
            raise ValueError(msg)
        invalid = next((profile for profile in self.profiles if not isinstance(profile, CapabilityProfile)), None)
        if invalid is not None:
            msg = f"unknown capability profile: {invalid}"
            raise TypeError(msg)


@dataclass(frozen=True, slots=True)
class AdapterSurface:
    """Identifiers owned by one focused MCP adapter."""

    adapter: str
    tools: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    resource_templates: tuple[str, ...] = ()
    prompts: tuple[str, ...] = ()
    profile_surfaces: tuple[ProfileSurface, ...] = field(default=(), compare=False, repr=False)

    def __post_init__(self) -> None:
        """Reject unnamed adapters at construction time."""
        if not self.adapter.strip():
            msg = "adapter name must not be empty"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class CombinedSurface:
    """Ordered identifiers combined from validated adapters."""

    tools: tuple[str, ...]
    resources: tuple[str, ...]
    resource_templates: tuple[str, ...]
    prompts: tuple[str, ...]


def validate_adapter_surfaces(surfaces: list[AdapterSurface] | tuple[AdapterSurface, ...]) -> None:
    """Reject duplicate adapter names or MCP identifiers."""
    adapter_names: set[str] = set()
    owners: dict[str, dict[str, str]] = {kind: {} for kind in _SURFACE_KINDS}
    for surface in surfaces:
        if surface.adapter in adapter_names:
            msg = f"duplicate adapter name: {surface.adapter}"
            raise ValueError(msg)
        adapter_names.add(surface.adapter)
        for kind, identifiers in _surface_entries(surface):
            local_identifiers: set[str] = set()
            for identifier in identifiers:
                if not identifier:
                    msg = f"empty {kind} identifier in adapter {surface.adapter}"
                    raise ValueError(msg)
                if identifier in local_identifiers:
                    msg = f"duplicate {kind} identifier {identifier!r} in adapter {surface.adapter!r}"
                    raise ValueError(msg)
                local_identifiers.add(identifier)
                previous_owner = owners[kind].get(identifier)
                if previous_owner is not None:
                    msg = (
                        f"duplicate {kind} identifier {identifier!r} declared by adapters "
                        f"{previous_owner!r} and {surface.adapter!r}"
                    )
                    raise ValueError(msg)
                owners[kind][identifier] = surface.adapter


def combine_adapter_surfaces(
    surfaces: list[AdapterSurface] | tuple[AdapterSurface, ...],
) -> CombinedSurface:
    """Combine validated adapter surfaces while preserving declaration order."""
    validate_adapter_surfaces(surfaces)
    return CombinedSurface(
        tools=tuple(identifier for surface in surfaces for identifier in surface.tools),
        resources=tuple(identifier for surface in surfaces for identifier in surface.resources),
        resource_templates=tuple(identifier for surface in surfaces for identifier in surface.resource_templates),
        prompts=tuple(identifier for surface in surfaces for identifier in surface.prompts),
    )


def validate_profiled_adapter_surfaces(
    surfaces: list[AdapterSurface] | tuple[AdapterSurface, ...],
) -> None:
    """Require one complete, full-compatible profile declaration per identifier."""
    validate_adapter_surfaces(surfaces)
    for surface in surfaces:
        expected = {kind: set(identifiers) for kind, identifiers in _surface_entries(surface)}
        declared: dict[str, set[str]] = {kind: set() for kind in _SURFACE_KINDS}
        for profile_surface in surface.profile_surfaces:
            if CapabilityProfile.FULL not in profile_surface.profiles:
                msg = f"profile declaration in adapter {surface.adapter!r} must include full profile"
                raise ValueError(msg)
            for kind, identifiers in _surface_entries(profile_surface):
                for identifier in identifiers:
                    if identifier not in expected[kind]:
                        msg = (
                            f"{kind} identifier {identifier!r} in adapter {surface.adapter!r} "
                            "is outside declared surface"
                        )
                        raise ValueError(msg)
                    if identifier in declared[kind]:
                        msg = (
                            f"duplicate profile declaration for {kind} identifier {identifier!r} "
                            f"in adapter {surface.adapter!r}"
                        )
                        raise ValueError(msg)
                    declared[kind].add(identifier)
        for kind in _SURFACE_KINDS:
            missing = expected[kind] - declared[kind]
            if missing:
                identifier = next(item for item in getattr(surface, kind) if item in missing)
                msg = f"missing profile declaration for {kind} identifier {identifier!r} in adapter {surface.adapter!r}"
                raise ValueError(msg)


def combine_adapter_surfaces_for_profile(
    surfaces: list[AdapterSurface] | tuple[AdapterSurface, ...],
    profile: CapabilityProfile,
) -> CombinedSurface:
    """Filter validated adapter declarations while preserving canonical order."""
    if not isinstance(profile, CapabilityProfile):
        msg = f"unknown capability profile: {profile}"
        raise TypeError(msg)
    validate_profiled_adapter_surfaces(surfaces)
    selected_surfaces = tuple(_adapter_surface_for_profile(surface, profile) for surface in surfaces)
    return combine_adapter_surfaces(selected_surfaces)


_SURFACE_KINDS = ("tools", "resources", "resource_templates", "prompts")


def _surface_entries(
    surface: AdapterSurface | ProfileSurface,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return (
        ("tools", surface.tools),
        ("resources", surface.resources),
        ("resource_templates", surface.resource_templates),
        ("prompts", surface.prompts),
    )


def _adapter_surface_for_profile(surface: AdapterSurface, profile: CapabilityProfile) -> AdapterSurface:
    selected: dict[str, set[str]] = {kind: set() for kind in _SURFACE_KINDS}
    for profile_surface in surface.profile_surfaces:
        if profile not in profile_surface.profiles:
            continue
        for kind, identifiers in _surface_entries(profile_surface):
            selected[kind].update(identifiers)
    return AdapterSurface(
        adapter=surface.adapter,
        tools=tuple(identifier for identifier in surface.tools if identifier in selected["tools"]),
        resources=tuple(identifier for identifier in surface.resources if identifier in selected["resources"]),
        resource_templates=tuple(
            identifier for identifier in surface.resource_templates if identifier in selected["resource_templates"]
        ),
        prompts=tuple(identifier for identifier in surface.prompts if identifier in selected["prompts"]),
    )
