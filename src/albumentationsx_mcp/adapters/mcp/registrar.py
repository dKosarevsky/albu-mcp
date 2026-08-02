"""Local registration port and profile-aware MCP decorator adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, TypeAlias

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface


class Handler(Protocol):
    """Function-like handler accepted by MCP decorators."""

    __name__: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


Decorator: TypeAlias = Callable[[Handler], Handler]


class McpRegistrar(Protocol):
    """Decorator surface required by AlbumentationsX MCP adapters."""

    tool: Any
    resource: Any
    prompt: Any


@dataclass(frozen=True, slots=True)
class _CollectedRegistration:
    kind: Literal["tool", "resource", "prompt"]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    handler: Handler


@dataclass(slots=True)
class CollectedMcpRegistrar:
    """Collect a validated registration batch before mutating an SDK server."""

    _registrations: list[_CollectedRegistration] = field(default_factory=list)

    def tool(self, name: str | None = None, **kwargs: Any) -> Decorator:
        return self._collect("tool", (name,), kwargs)

    def resource(self, uri: str, **kwargs: Any) -> Decorator:
        return self._collect("resource", (uri,), kwargs)

    def prompt(self, name: str | None = None, **kwargs: Any) -> Decorator:
        return self._collect("prompt", (name,), kwargs)

    def apply_to(self, target: McpRegistrar) -> None:
        """Apply the complete batch in declaration order."""
        for registration in self._registrations:
            decorator_factory = getattr(target, registration.kind)
            decorator_factory(*registration.args, **registration.kwargs)(registration.handler)

    def _collect(
        self,
        kind: Literal["tool", "resource", "prompt"],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Decorator:
        def decorator(handler: Handler) -> Handler:
            self._registrations.append(
                _CollectedRegistration(
                    kind=kind,
                    args=args,
                    kwargs=dict(kwargs),
                    handler=handler,
                )
            )
            return handler

        return decorator


@dataclass(slots=True)
class ProfiledMcpRegistrar:
    """Validate adapter ownership and delegate only profile-selected items."""

    target: McpRegistrar
    declared: AdapterSurface
    selected: AdapterSurface
    _seen: dict[str, list[str]] = field(
        init=False,
        default_factory=lambda: {
            "tools": [],
            "resources": [],
            "resource_templates": [],
            "prompts": [],
        },
    )

    def __post_init__(self) -> None:
        """Reject profile selections outside the adapter declaration."""
        if self.selected.adapter != self.declared.adapter:
            msg = "selected MCP surface must belong to the declared adapter"
            raise ValueError(msg)
        for kind in self._seen:
            unexpected = set(getattr(self.selected, kind)) - set(getattr(self.declared, kind))
            if unexpected:
                identifier = next(iter(unexpected))
                msg = f"selected {kind} identifier {identifier!r} is not declared by {self.declared.adapter!r}"
                raise ValueError(msg)

    def tool(self, name: str | None = None, **kwargs: Any) -> Decorator:
        def decorator(handler: Handler) -> Handler:
            identifier = name or handler.__name__
            if self._record("tools", identifier):
                return self.target.tool(name=name, **kwargs)(handler)
            return handler

        return decorator

    def resource(self, uri: str, **kwargs: Any) -> Decorator:
        def decorator(handler: Handler) -> Handler:
            kind = self._resource_kind(uri)
            if self._record(kind, uri):
                return self.target.resource(uri, **kwargs)(handler)
            return handler

        return decorator

    def prompt(self, name: str | None = None, **kwargs: Any) -> Decorator:
        def decorator(handler: Handler) -> Handler:
            identifier = name or handler.__name__
            if self._record("prompts", identifier):
                return self.target.prompt(name=name, **kwargs)(handler)
            return handler

        return decorator

    def verify_complete(self) -> None:
        """Require the adapter implementation to match its declaration exactly."""
        actual = AdapterSurface(
            adapter=self.declared.adapter,
            tools=tuple(self._seen["tools"]),
            resources=tuple(self._seen["resources"]),
            resource_templates=tuple(self._seen["resource_templates"]),
            prompts=tuple(self._seen["prompts"]),
        )
        if actual != self.declared:
            msg = (
                f"adapter {self.declared.adapter!r} did not register its declared surface: "
                f"expected {self.declared!r}, got {actual!r}"
            )
            raise RuntimeError(msg)

    def _resource_kind(self, uri: str) -> str:
        if uri in self.declared.resources:
            return "resources"
        if uri in self.declared.resource_templates:
            return "resource_templates"
        return "resources"

    def _record(self, kind: str, identifier: str) -> bool:
        declared = getattr(self.declared, kind)
        if identifier not in declared:
            msg = f"adapter {self.declared.adapter!r} registered undeclared {kind} identifier {identifier!r}"
            raise RuntimeError(msg)
        if identifier in self._seen[kind]:
            msg = f"adapter {self.declared.adapter!r} registered duplicate {kind} identifier {identifier!r}"
            raise RuntimeError(msg)
        self._seen[kind].append(identifier)
        return identifier in getattr(self.selected, kind)
