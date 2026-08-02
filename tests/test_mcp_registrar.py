from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pytest

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface
from albumentationsx_mcp.adapters.mcp.registrar import ProfiledMcpRegistrar


class RecordingRegistrar:
    def __init__(self) -> None:
        self.tools: list[str] = []
        self.resources: list[str] = []
        self.prompts: list[str] = []

    def tool(self, name: str | None = None, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._record(self.tools, name)

    def resource(self, uri: str, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._record(self.resources, uri)

    def prompt(self, name: str | None = None, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._record(self.prompts, name)

    @staticmethod
    def _record(
        destination: list[str],
        explicit_name: str | None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            destination.append(explicit_name or cast("Any", handler).__name__)
            return handler

        return decorator


def test_profiled_registrar_validates_full_declaration_and_delegates_selected_items() -> None:
    target = RecordingRegistrar()
    declared = AdapterSurface(
        adapter="example",
        tools=("hidden_tool", "public_tool"),
        resources=("example://static",),
        resource_templates=("example://{item}",),
        prompts=("public_prompt",),
    )
    selected = AdapterSurface(
        adapter="example",
        tools=("public_tool",),
        resource_templates=("example://{item}",),
        prompts=("public_prompt",),
    )
    registrar = ProfiledMcpRegistrar(target, declared=declared, selected=selected)

    @registrar.tool()
    def hidden_tool() -> str:
        return "hidden"

    @registrar.tool(name="public_tool")
    def renamed_tool() -> str:
        return "public"

    @registrar.resource("example://static")
    def static_resource() -> str:
        return "static"

    @registrar.resource("example://{item}")
    def template_resource(item: str) -> str:
        return item

    @registrar.prompt(name="public_prompt")
    def renamed_prompt() -> str:
        return "prompt"

    registrar.verify_complete()

    assert target.tools == ["public_tool"]
    assert target.resources == ["example://{item}"]
    assert target.prompts == ["public_prompt"]


def test_profiled_registrar_rejects_undeclared_identifier_before_delegation() -> None:
    target = RecordingRegistrar()
    registrar = ProfiledMcpRegistrar(
        target,
        declared=AdapterSurface(adapter="example", tools=("declared",)),
        selected=AdapterSurface(adapter="example", tools=("declared",)),
    )

    with pytest.raises(RuntimeError, match="undeclared tools identifier 'unexpected'"):

        @registrar.tool()
        def unexpected() -> str:
            return "unexpected"

    assert target.tools == []


def test_profiled_registrar_reports_missing_declarations() -> None:
    registrar = ProfiledMcpRegistrar(
        RecordingRegistrar(),
        declared=AdapterSurface(adapter="example", tools=("missing",)),
        selected=AdapterSurface(adapter="example", tools=("missing",)),
    )

    with pytest.raises(RuntimeError, match="did not register its declared surface"):
        registrar.verify_complete()
