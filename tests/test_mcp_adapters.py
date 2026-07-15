from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pytest
from mcp.server.fastmcp import FastMCP

from albumentationsx_mcp.adapters.mcp import registration as registration_module
from albumentationsx_mcp.adapters.mcp.catalog import SURFACE as CATALOG_SURFACE
from albumentationsx_mcp.adapters.mcp.catalog import register_catalog_adapter
from albumentationsx_mcp.adapters.mcp.contracts import (
    AdapterSurface,
    combine_adapter_surfaces,
    validate_adapter_surfaces,
)
from albumentationsx_mcp.adapters.mcp.dataset import SURFACE as DATASET_SURFACE
from albumentationsx_mcp.adapters.mcp.dataset import register_dataset_adapter
from albumentationsx_mcp.adapters.mcp.dependencies import McpDependencies
from albumentationsx_mcp.adapters.mcp.diagnostics import SURFACE as DIAGNOSTICS_SURFACE
from albumentationsx_mcp.adapters.mcp.diagnostics import register_diagnostics_adapter
from albumentationsx_mcp.adapters.mcp.policy import SURFACE as POLICY_SURFACE
from albumentationsx_mcp.adapters.mcp.policy import register_policy_adapter
from albumentationsx_mcp.adapters.mcp.preview import SURFACE as PREVIEW_SURFACE
from albumentationsx_mcp.adapters.mcp.preview import register_preview_adapter
from albumentationsx_mcp.adapters.mcp.prompts import SURFACE as PROMPT_SURFACE
from albumentationsx_mcp.adapters.mcp.prompts import register_prompt_adapter
from albumentationsx_mcp.adapters.mcp.registration import (
    ADAPTER_SURFACES,
    COMBINED_SURFACE,
    register_mcp_adapters,
)
from albumentationsx_mcp.adapters.mcp.sessions import SURFACE as SESSION_SURFACE
from albumentationsx_mcp.adapters.mcp.sessions import register_session_adapter
from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.diagnostics import DiagnosticsService, PublicSurface
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.preview import ArtifactStore, PathPolicy, PreviewService
from albumentationsx_mcp.preview_validation import PreviewRequestValidator
from albumentationsx_mcp.reports import PreviewReportService
from albumentationsx_mcp.review import PreviewFeedbackStore
from albumentationsx_mcp.sessions import InteractiveTuningSessionStore
from albumentationsx_mcp.tuning import TuningDecisionStore
from scripts.export_mcp_contract import build_contract_snapshot

_CONTRACT_SNAPSHOT_PATH = Path("tests/fixtures/snapshots/mcp_contract.json")
SurfaceField = Literal["tools", "resources", "resource_templates", "prompts"]


@dataclass(frozen=True)
class AdapterTestDependencies:
    catalog: TransformCatalog
    pipeline_service: PipelineService
    path_policy: PathPolicy
    artifact_store: ArtifactStore
    preview_service: PreviewService
    preview_validator: PreviewRequestValidator
    tuning_store: TuningDecisionStore
    session_store: InteractiveTuningSessionStore
    feedback_store: PreviewFeedbackStore
    report_service: PreviewReportService
    diagnostics_service: DiagnosticsService


@pytest.fixture
def adapter_dependencies(tmp_path: Path) -> AdapterTestDependencies:
    catalog = TransformCatalog()
    pipeline_service = PipelineService(catalog)
    path_policy = PathPolicy([tmp_path])
    artifact_root = tmp_path / "artifacts"
    artifact_store = ArtifactStore(artifact_root)
    preview_service = PreviewService(
        pipeline_service,
        path_policy,
        artifact_store,
    )
    preview_validator = PreviewRequestValidator(
        pipeline_service=pipeline_service,
        path_policy=path_policy,
    )
    diagnostics_service = DiagnosticsService(
        allowed_roots=[tmp_path],
        artifact_root=artifact_root,
        max_preview_runs=100,
        public_surface=PublicSurface(tools=[], prompts=[], workflow_resources=[]),
    )
    return AdapterTestDependencies(
        catalog=catalog,
        pipeline_service=pipeline_service,
        path_policy=path_policy,
        artifact_store=artifact_store,
        preview_service=preview_service,
        preview_validator=preview_validator,
        tuning_store=TuningDecisionStore(artifact_root),
        session_store=InteractiveTuningSessionStore(artifact_root),
        feedback_store=PreviewFeedbackStore(artifact_root),
        report_service=PreviewReportService(artifact_root),
        diagnostics_service=diagnostics_service,
    )


def test_combine_adapter_surfaces_preserves_declared_order() -> None:
    surface = combine_adapter_surfaces(
        [
            AdapterSurface(
                adapter="catalog",
                tools=("search_transforms",),
                resources=("catalog://all",),
                resource_templates=("catalog://{name}",),
            ),
            AdapterSurface(
                adapter="policy",
                tools=("validate_pipeline",),
                prompts=("policy_prompt",),
            ),
        ]
    )

    assert surface.tools == ("search_transforms", "validate_pipeline")
    assert surface.resources == ("catalog://all",)
    assert surface.resource_templates == ("catalog://{name}",)
    assert surface.prompts == ("policy_prompt",)


def test_adapter_surface_rejects_empty_adapter_name() -> None:
    with pytest.raises(ValueError, match="adapter name must not be empty"):
        AdapterSurface(adapter="")


def test_validate_adapter_surfaces_rejects_duplicate_adapter_name() -> None:
    surfaces = [
        AdapterSurface(adapter="catalog", tools=("search_transforms",)),
        AdapterSurface(adapter="catalog", tools=("get_transform_schema",)),
    ]

    with pytest.raises(ValueError, match="duplicate adapter name: catalog"):
        validate_adapter_surfaces(surfaces)


@pytest.mark.parametrize(
    ("field", "identifier"),
    [
        ("tools", "search_transforms"),
        ("resources", "albumentationsx://capabilities"),
        ("resource_templates", "albumentationsx://transforms/{name}"),
        ("prompts", "run_first_preview_review"),
    ],
)
def test_validate_adapter_surfaces_rejects_duplicate_identifier_within_adapter(
    field: SurfaceField,
    identifier: str,
) -> None:
    surface = _surface_with_identifiers("catalog", field, (identifier, identifier))

    with pytest.raises(ValueError, match=f"duplicate {field} identifier") as error:
        validate_adapter_surfaces([surface])

    message = str(error.value)
    assert field in message
    assert identifier in message
    assert "catalog" in message


@pytest.mark.parametrize(
    ("field", "identifier"),
    [
        ("tools", "search_transforms"),
        ("resources", "albumentationsx://capabilities"),
        ("resource_templates", "albumentationsx://transforms/{name}"),
        ("prompts", "run_first_preview_review"),
    ],
)
def test_validate_adapter_surfaces_rejects_identifier_owned_by_two_adapters(
    field: SurfaceField,
    identifier: str,
) -> None:
    surfaces = [
        _surface_with_identifiers("catalog", field, (identifier,)),
        _surface_with_identifiers("policy", field, (identifier,)),
    ]

    with pytest.raises(ValueError, match=f"duplicate {field} identifier") as error:
        validate_adapter_surfaces(surfaces)

    message = str(error.value)
    assert field in message
    assert identifier in message
    assert "catalog" in message
    assert "policy" in message


def test_catalog_adapter_registers_its_exact_declared_surface() -> None:
    mcp = FastMCP("catalog-test")

    register_catalog_adapter(mcp, catalog=TransformCatalog())

    assert _registered_surface(mcp, adapter="catalog") == CATALOG_SURFACE
    _assert_registered_contract_matches_snapshot(mcp, CATALOG_SURFACE)


def test_policy_adapter_registers_its_exact_declared_surface() -> None:
    mcp = FastMCP("policy-test")
    catalog = TransformCatalog()

    register_policy_adapter(mcp, catalog=catalog, pipeline_service=PipelineService(catalog))

    assert _registered_surface(mcp, adapter="policy") == POLICY_SURFACE
    _assert_registered_contract_matches_snapshot(mcp, POLICY_SURFACE)


def test_dataset_adapter_registers_its_exact_declared_surface(
    adapter_dependencies: AdapterTestDependencies,
) -> None:
    mcp = FastMCP("dataset-test")

    register_dataset_adapter(
        mcp,
        path_policy=adapter_dependencies.path_policy,
        pipeline_service=adapter_dependencies.pipeline_service,
        preview_service=adapter_dependencies.preview_service,
    )

    assert _registered_surface(mcp, adapter="dataset") == DATASET_SURFACE
    _assert_registered_contract_matches_snapshot(mcp, DATASET_SURFACE)


def test_diagnostics_adapter_registers_its_exact_declared_surface(
    adapter_dependencies: AdapterTestDependencies,
) -> None:
    mcp = FastMCP("diagnostics-test")

    register_diagnostics_adapter(
        mcp,
        diagnostics_service=adapter_dependencies.diagnostics_service,
        pipeline_service=adapter_dependencies.pipeline_service,
    )

    assert _registered_surface(mcp, adapter="diagnostics") == DIAGNOSTICS_SURFACE
    _assert_registered_contract_matches_snapshot(mcp, DIAGNOSTICS_SURFACE)


def test_prompt_adapter_registers_its_exact_declared_surface() -> None:
    mcp = FastMCP("prompts-test")

    register_prompt_adapter(mcp)

    assert _registered_surface(mcp, adapter="prompts") == PROMPT_SURFACE
    _assert_registered_contract_matches_snapshot(mcp, PROMPT_SURFACE)


def test_preview_adapter_registers_its_exact_declared_surface(
    adapter_dependencies: AdapterTestDependencies,
) -> None:
    mcp = FastMCP("preview-test")

    register_preview_adapter(
        mcp,
        artifact_store=adapter_dependencies.artifact_store,
        preview_service=adapter_dependencies.preview_service,
        preview_validator=adapter_dependencies.preview_validator,
        tuning_store=adapter_dependencies.tuning_store,
        session_store=adapter_dependencies.session_store,
        feedback_store=adapter_dependencies.feedback_store,
        report_service=adapter_dependencies.report_service,
    )

    assert _registered_surface(mcp, adapter="preview") == PREVIEW_SURFACE
    _assert_registered_contract_matches_snapshot(mcp, PREVIEW_SURFACE)


def test_session_adapter_registers_its_exact_declared_surface(
    adapter_dependencies: AdapterTestDependencies,
) -> None:
    mcp = FastMCP("sessions-test")

    register_session_adapter(
        mcp,
        preview_service=adapter_dependencies.preview_service,
        tuning_store=adapter_dependencies.tuning_store,
        session_store=adapter_dependencies.session_store,
        feedback_store=adapter_dependencies.feedback_store,
    )

    assert _registered_surface(mcp, adapter="sessions") == SESSION_SURFACE
    _assert_registered_contract_matches_snapshot(mcp, SESSION_SURFACE)


def test_combined_adapter_surface_matches_canonical_counts() -> None:
    assert tuple(surface.adapter for surface in ADAPTER_SURFACES) == (
        "catalog",
        "policy",
        "dataset",
        "preview",
        "sessions",
        "diagnostics",
        "prompts",
    )
    assert len(COMBINED_SURFACE.tools) == 45
    assert len(COMBINED_SURFACE.resources) == 20
    assert len(COMBINED_SURFACE.resource_templates) == 2
    assert len(COMBINED_SURFACE.prompts) == 5


def test_register_mcp_adapters_registers_exact_combined_surface(
    adapter_dependencies: AdapterTestDependencies,
) -> None:
    mcp = FastMCP("combined-test")

    register_mcp_adapters(mcp, _mcp_dependencies(adapter_dependencies))

    assert tuple(mcp._tool_manager._tools) == COMBINED_SURFACE.tools
    assert tuple(str(uri) for uri in mcp._resource_manager._resources) == COMBINED_SURFACE.resources
    assert tuple(mcp._resource_manager._templates) == COMBINED_SURFACE.resource_templates
    assert tuple(mcp._prompt_manager._prompts) == COMBINED_SURFACE.prompts


def test_register_mcp_adapters_rejects_collision_before_partial_registration(
    adapter_dependencies: AdapterTestDependencies,
) -> None:
    mcp = FastMCP("collision-test")

    @mcp.tool(name="search_transforms")
    def existing_search_transforms() -> str:
        return "existing"

    with pytest.raises(ValueError, match=r"tools.*search_transforms"):
        register_mcp_adapters(mcp, _mcp_dependencies(adapter_dependencies))

    assert tuple(mcp._tool_manager._tools) == ("search_transforms",)
    assert not mcp._resource_manager._resources
    assert not mcp._resource_manager._templates
    assert not mcp._prompt_manager._prompts


def test_register_mcp_adapters_rolls_back_unexpected_registration_failure(
    adapter_dependencies: AdapterTestDependencies,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mcp = FastMCP("rollback-test")

    @mcp.tool(name="existing_tool")
    def existing_tool() -> str:
        return "existing"

    def failing_session_adapter(target: FastMCP, **_: Any) -> None:
        @target.tool(name="partially_registered_tool")
        def partially_registered_tool() -> str:
            return "partial"

        message = "injected registration failure"
        raise RuntimeError(message)

    monkeypatch.setattr(registration_module, "register_session_adapter", failing_session_adapter)

    with pytest.raises(RuntimeError, match="injected registration failure"):
        register_mcp_adapters(mcp, _mcp_dependencies(adapter_dependencies))

    assert tuple(mcp._tool_manager._tools) == ("existing_tool",)
    assert not mcp._resource_manager._resources
    assert not mcp._resource_manager._templates
    assert not mcp._prompt_manager._prompts


def _registered_surface(mcp: FastMCP, *, adapter: str) -> AdapterSurface:
    return AdapterSurface(
        adapter=adapter,
        tools=tuple(mcp._tool_manager._tools),
        resources=tuple(str(uri) for uri in mcp._resource_manager._resources),
        resource_templates=tuple(mcp._resource_manager._templates),
        prompts=tuple(mcp._prompt_manager._prompts),
    )


def _surface_with_identifiers(
    adapter: str,
    field: SurfaceField,
    identifiers: tuple[str, ...],
) -> AdapterSurface:
    if field == "tools":
        return AdapterSurface(adapter=adapter, tools=identifiers)
    if field == "resources":
        return AdapterSurface(adapter=adapter, resources=identifiers)
    if field == "resource_templates":
        return AdapterSurface(adapter=adapter, resource_templates=identifiers)
    return AdapterSurface(adapter=adapter, prompts=identifiers)


def _mcp_dependencies(dependencies: AdapterTestDependencies) -> McpDependencies:
    return McpDependencies(
        catalog=dependencies.catalog,
        pipeline_service=dependencies.pipeline_service,
        path_policy=dependencies.path_policy,
        artifact_store=dependencies.artifact_store,
        preview_service=dependencies.preview_service,
        preview_validator=dependencies.preview_validator,
        tuning_store=dependencies.tuning_store,
        session_store=dependencies.session_store,
        feedback_store=dependencies.feedback_store,
        report_service=dependencies.report_service,
        diagnostics_service=dependencies.diagnostics_service,
    )


def _assert_registered_contract_matches_snapshot(mcp: FastMCP, surface: AdapterSurface) -> None:
    expected = json.loads(_CONTRACT_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    actual = build_contract_snapshot(mcp)

    assert _contract_fragment(actual, surface) == _contract_fragment(expected, surface)


def _contract_fragment(snapshot: dict[str, Any], surface: AdapterSurface) -> dict[str, Any]:
    tools = snapshot["tools"]
    resources = snapshot["resources"]
    resource_templates = snapshot["resource_templates"]
    prompts = snapshot["prompts"]
    assert isinstance(tools, list)
    assert isinstance(resources, list)
    assert isinstance(resource_templates, list)
    assert isinstance(prompts, list)
    return {
        "tools": [entry for entry in tools if entry["name"] in surface.tools],
        "resources": [entry for entry in resources if entry["uri"] in surface.resources],
        "resource_templates": [
            entry for entry in resource_templates if entry["uri_template"] in surface.resource_templates
        ],
        "prompts": [entry for entry in prompts if entry["name"] in surface.prompts],
    }
