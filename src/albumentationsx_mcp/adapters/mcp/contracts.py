"""Pure contracts for declared MCP adapter ownership."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdapterSurface:
    """Identifiers owned by one focused MCP adapter."""

    adapter: str
    tools: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    resource_templates: tuple[str, ...] = ()
    prompts: tuple[str, ...] = ()

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


_SURFACE_KINDS = ("tools", "resources", "resource_templates", "prompts")


def _surface_entries(surface: AdapterSurface) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return (
        ("tools", surface.tools),
        ("resources", surface.resources),
        ("resource_templates", surface.resource_templates),
        ("prompts", surface.prompts),
    )
