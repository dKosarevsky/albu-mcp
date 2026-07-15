from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from albumentationsx_mcp.capabilities import CapabilityProfile
from albumentationsx_mcp.server import ServerSettings, create_mcp_server
from albumentationsx_mcp.workflows import HOST_EXAMPLE_IDS, HostExampleId
from scripts.export_mcp_contract import build_contract_snapshot

_EXPECTED_EXAMPLE_IDS = (
    "client-smoke",
    "first-preview",
    "distortion-review",
    "dataset-onboarding",
    "diagnostics",
    "review-loop",
    "report-handoff",
)


@pytest.fixture(scope="module")
def workflow_server() -> Any:
    return create_mcp_server()


def test_workflow_example_ids_are_closed_and_stable() -> None:
    assert HOST_EXAMPLE_IDS == _EXPECTED_EXAMPLE_IDS


@pytest.mark.parametrize("example_id", _EXPECTED_EXAMPLE_IDS)
def test_workflow_example_tool_matches_resource_payload(
    workflow_server: Any,
    example_id: HostExampleId,
) -> None:
    tool = workflow_server._tool_manager._tools["get_workflow_example"]
    resource = workflow_server._resource_manager._resources[f"albumentationsx://examples/{example_id}"]

    assert tool.fn(example_id=example_id) == json.loads(resource.fn())


def test_workflow_example_tool_schema_uses_closed_identifier_enum(workflow_server: Any) -> None:
    snapshot = build_contract_snapshot(workflow_server)
    tool = next(entry for entry in snapshot["tools"] if entry["name"] == "get_workflow_example")

    assert tool["parameters"]["properties"]["example_id"]["enum"] == list(_EXPECTED_EXAMPLE_IDS)


@pytest.mark.parametrize("profile", CapabilityProfile)
def test_workflow_example_fallback_respects_profile_resource_view(
    tmp_path: Path,
    profile: CapabilityProfile,
) -> None:
    server = create_mcp_server(
        ServerSettings(
            allowed_roots=[tmp_path],
            artifact_root=tmp_path / "artifacts",
            capability_profile=profile,
        )
    )
    tool = server._tool_manager._tools["get_workflow_example"]
    resources = server._resource_manager._resources

    for example_id in HOST_EXAMPLE_IDS:
        uri = f"albumentationsx://examples/{example_id}"
        if uri in resources:
            resource = resources[uri]
            assert tool.fn(example_id=example_id) == json.loads(cast("Any", resource).fn())
            continue
        with pytest.raises(ValueError, match=f"capability profile {profile.value!r}"):
            tool.fn(example_id=example_id)


def test_fallback_tool_is_part_of_the_committed_public_contract() -> None:
    snapshot = json.loads(Path("tests/fixtures/snapshots/mcp_contract.json").read_text(encoding="utf-8"))

    assert "get_workflow_example" in {entry["name"] for entry in snapshot["tools"]}
