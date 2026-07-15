"""Pure ownership contracts for grouped CLI commands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CliGroupSurface:
    """Commands owned by one public top-level CLI group."""

    group: str
    commands: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject unnamed public command groups."""
        if not self.group.strip():
            message = "CLI group name must not be empty"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class CombinedCliSurface:
    """Ordered public CLI groups and fully qualified command paths."""

    groups: tuple[str, ...]
    command_paths: tuple[str, ...]


def validate_cli_group_surfaces(surfaces: tuple[CliGroupSurface, ...]) -> None:
    """Reject duplicate groups and empty or duplicate commands."""
    groups: set[str] = set()
    for surface in surfaces:
        if surface.group in groups:
            message = f"duplicate CLI group: {surface.group}"
            raise ValueError(message)
        groups.add(surface.group)

        commands: set[str] = set()
        for command in surface.commands:
            if not command.strip():
                message = f"empty CLI command in group {surface.group!r}"
                raise ValueError(message)
            if command in commands:
                message = f"duplicate CLI command {command!r} in group {surface.group!r}"
                raise ValueError(message)
            commands.add(command)


def combine_cli_group_surfaces(surfaces: tuple[CliGroupSurface, ...]) -> CombinedCliSurface:
    """Combine validated surfaces while preserving declaration order."""
    validate_cli_group_surfaces(surfaces)
    return CombinedCliSurface(
        groups=tuple(surface.group for surface in surfaces),
        command_paths=tuple(f"{surface.group} {command}" for surface in surfaces for command in surface.commands),
    )
