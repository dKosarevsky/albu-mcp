from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

from albumentationsx_mcp.adapters.mcp.catalog import SURFACE as CATALOG_SURFACE
from albumentationsx_mcp.adapters.mcp.catalog import register_catalog_adapter
from albumentationsx_mcp.adapters.mcp.contracts import (
    AdapterSurface,
    combine_adapter_surfaces,
    validate_adapter_surfaces,
)
from albumentationsx_mcp.adapters.mcp.dataset import SURFACE as DATASET_SURFACE
from albumentationsx_mcp.adapters.mcp.dataset import register_dataset_adapter
from albumentationsx_mcp.adapters.mcp.diagnostics import SURFACE as DIAGNOSTICS_SURFACE
from albumentationsx_mcp.adapters.mcp.diagnostics import register_diagnostics_adapter
from albumentationsx_mcp.adapters.mcp.policy import SURFACE as POLICY_SURFACE
from albumentationsx_mcp.adapters.mcp.policy import register_policy_adapter
from albumentationsx_mcp.adapters.mcp.prompts import SURFACE as PROMPT_SURFACE
from albumentationsx_mcp.adapters.mcp.prompts import register_prompt_adapter
from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.diagnostics import DiagnosticsService, PublicSurface
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.preview import ArtifactStore, PathPolicy, PreviewService


@dataclass(frozen=True)
class AdapterTestDependencies:
    catalog: TransformCatalog
    pipeline_service: PipelineService
    path_policy: PathPolicy
    preview_service: PreviewService
    diagnostics_service: DiagnosticsService


@pytest.fixture
def adapter_dependencies(tmp_path: Path) -> AdapterTestDependencies:
    catalog = TransformCatalog()
    pipeline_service = PipelineService(catalog)
    path_policy = PathPolicy([tmp_path])
    artifact_root = tmp_path / "artifacts"
    preview_service = PreviewService(
        pipeline_service,
        path_policy,
        ArtifactStore(artifact_root),
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
        preview_service=preview_service,
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
    field: str,
    identifier: str,
) -> None:
    surface = AdapterSurface(adapter="catalog", **{field: (identifier, identifier)})

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
    field: str,
    identifier: str,
) -> None:
    surfaces = [
        AdapterSurface(adapter="catalog", **{field: (identifier,)}),
        AdapterSurface(adapter="policy", **{field: (identifier,)}),
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


def test_policy_adapter_registers_its_exact_declared_surface() -> None:
    mcp = FastMCP("policy-test")
    catalog = TransformCatalog()

    register_policy_adapter(mcp, catalog=catalog, pipeline_service=PipelineService(catalog))

    assert _registered_surface(mcp, adapter="policy") == POLICY_SURFACE


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


def test_prompt_adapter_registers_its_exact_declared_surface() -> None:
    mcp = FastMCP("prompts-test")

    register_prompt_adapter(mcp)

    assert _registered_surface(mcp, adapter="prompts") == PROMPT_SURFACE


def _registered_surface(mcp: FastMCP, *, adapter: str) -> AdapterSurface:
    return AdapterSurface(
        adapter=adapter,
        tools=tuple(mcp._tool_manager._tools),
        resources=tuple(str(uri) for uri in mcp._resource_manager._resources),
        resource_templates=tuple(mcp._resource_manager._templates),
        prompts=tuple(mcp._prompt_manager._prompts),
    )
