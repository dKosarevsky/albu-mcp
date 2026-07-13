"""Export a deterministic snapshot of the public FastMCP contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from albumentationsx_mcp.server import create_mcp_server

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def build_contract_snapshot(server: FastMCP | None = None) -> dict[str, Any]:
    """Return the public MCP surface as canonical JSON-compatible data."""
    server = server or create_mcp_server()
    return {
        "server": {
            "name": server.name,
        },
        "tools": [
            _tool_entry(tool)
            for _, tool in sorted(server._tool_manager._tools.items())  # noqa: SLF001
        ],
        "resources": [
            _resource_entry(resource)
            for _, resource in sorted(server._resource_manager._resources.items())  # noqa: SLF001
        ],
        "resource_templates": [
            _resource_template_entry(template)
            for _, template in sorted(server._resource_manager._templates.items())  # noqa: SLF001
        ],
        "prompts": [
            _prompt_entry(prompt)
            for _, prompt in sorted(server._prompt_manager._prompts.items())  # noqa: SLF001
        ],
    }


def dump_contract_snapshot(snapshot: dict[str, Any]) -> str:
    """Serialize a snapshot with stable formatting."""
    return json.dumps(_json_safe(snapshot), indent=2, sort_keys=True) + "\n"


def main() -> None:
    """Write the current MCP contract snapshot to stdout or a file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional path to write the snapshot JSON.")
    args = parser.parse_args()

    content = dump_contract_snapshot(build_contract_snapshot())
    if args.output is None:
        sys.stdout.write(content)
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _tool_entry(tool: Any) -> dict[str, Any]:
    return _with_meta(
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": _json_safe(tool.parameters),
        },
        tool.meta,
    )


def _resource_entry(resource: Any) -> dict[str, Any]:
    return _with_meta(
        {
            "uri": str(resource.uri),
            "name": resource.name,
            "description": resource.description,
            "mime_type": resource.mime_type,
        },
        resource.meta,
    )


def _resource_template_entry(template: Any) -> dict[str, Any]:
    return _with_meta(
        {
            "uri_template": template.uri_template,
            "name": template.name,
            "description": template.description,
            "mime_type": template.mime_type,
            "parameters": _json_safe(template.parameters),
        },
        template.meta,
    )


def _prompt_entry(prompt: Any) -> dict[str, Any]:
    return {
        "name": prompt.name,
        "description": prompt.description,
        "arguments": [
            {
                "name": argument.name,
                "description": argument.description,
                "required": argument.required,
            }
            for argument in prompt.arguments
        ],
    }


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _with_meta(entry: dict[str, Any], meta: Any) -> dict[str, Any]:
    if meta is not None:
        entry["meta"] = _json_safe(meta)
    return entry


if __name__ == "__main__":
    main()
