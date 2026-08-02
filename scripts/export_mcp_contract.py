"""Export a deterministic snapshot of the public MCP contract."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.shared.uri_template import UriTemplate

from albumentationsx_mcp.server import create_mcp_server

if TYPE_CHECKING:
    from mcp.server import MCPServer

_RESOURCE_TEMPLATE_TITLE_OVERRIDES = {
    "artifact://{run_id}/{filename}": "preview_image_artifactArguments",
}


def build_contract_snapshot(server: MCPServer | None = None) -> dict[str, Any]:
    """Return the public MCP surface as canonical JSON-compatible data."""
    return asyncio.run(build_contract_snapshot_async(server))


async def build_contract_snapshot_async(server: MCPServer | None = None) -> dict[str, Any]:
    """Return the public MCP surface through SDK-supported listing APIs."""
    active_server = server or create_mcp_server()
    tools, resources, templates, prompts = await asyncio.gather(
        active_server.list_tools(),
        active_server.list_resources(),
        active_server.list_resource_templates(),
        active_server.list_prompts(),
    )
    return {
        "server": {
            "name": active_server.name,
        },
        "tools": [_tool_entry(tool) for tool in sorted(tools, key=lambda item: item.name)],
        "resources": [_resource_entry(resource) for resource in sorted(resources, key=lambda item: str(item.uri))],
        "resource_templates": [
            _resource_template_entry(template) for template in sorted(templates, key=lambda item: item.uri_template)
        ],
        "prompts": [_prompt_entry(prompt) for prompt in sorted(prompts, key=lambda item: item.name)],
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
            "parameters": _json_safe(tool.input_schema),
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
            "parameters": _resource_template_parameters(template.uri_template, template.name),
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
            for argument in prompt.arguments or []
        ],
    }


def _resource_template_parameters(uri_template: str, template_name: str) -> dict[str, Any]:
    variable_names = UriTemplate.parse(uri_template).variable_names
    title = _RESOURCE_TEMPLATE_TITLE_OVERRIDES.get(uri_template, f"{template_name}Arguments")
    return {
        "properties": {
            name: {
                "title": name.replace("_", " ").title(),
                "type": "string",
            }
            for name in variable_names
        },
        "required": variable_names,
        "title": title,
        "type": "object",
    }


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _with_meta(entry: dict[str, Any], meta: Any) -> dict[str, Any]:
    if meta is not None:
        entry["meta"] = _json_safe(meta)
    return entry


if __name__ == "__main__":
    main()
