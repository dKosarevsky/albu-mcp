from __future__ import annotations

from typing import Any

import pytest

from albumentationsx_mcp.server import create_mcp_server
from scripts.export_mcp_contract import build_contract_snapshot


@pytest.fixture(scope="module")
def tensor_server() -> Any:
    return create_mcp_server()


def test_pipeline_tools_expose_tensor_input_contract(tensor_server: Any) -> None:
    snapshot = build_contract_snapshot(tensor_server)
    tools = {entry["name"]: entry for entry in snapshot["tools"]}

    assert "input_contract" in tools["validate_pipeline"]["parameters"]["properties"]
    assert "input_contract" in tools["export_pipeline"]["parameters"]["properties"]
    assert "target" in tools["export_pipeline"]["parameters"]["properties"]


def test_validate_pipeline_reports_unreleased_tensor_runtime_through_mcp(tensor_server: Any) -> None:
    validate = tensor_server._tool_manager._tools["validate_pipeline"]

    result = validate.fn(
        pipeline={"transforms": [{"name": "NoOp"}]},
        target={"targets": ["image"]},
        input_contract={
            "representation": "torch",
            "device": "cpu",
            "requires_grad": False,
            "targets": [{"name": "image", "shape": [3, None, None], "dtype": "uint8"}],
        },
    )

    assert result["valid"] is False
    assert result["tensor_compatibility"]["status"] == "runtime_unavailable"
    assert result["errors"][0]["code"] == "cpu_tensor_runtime_unavailable"
