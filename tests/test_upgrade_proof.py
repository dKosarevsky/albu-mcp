from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

import pytest

from albumentationsx_mcp.upgrade_proof import (
    ArtifactContinuity,
    ProtocolObservation,
    PublicSurface,
    build_upgrade_proof_report,
)


def _surface(*, extra_tool: str | None = None) -> PublicSurface:
    tools = ["render_preview_batch", "search_transforms"]
    if extra_tool is not None:
        tools.append(extra_tool)
    return PublicSurface.build(
        tools=tools,
        resources=["albumentationsx://examples/client-smoke"],
        resource_templates=["albumentationsx://preview-artifacts/{run_id}/{filename}"],
        prompts=["augment_dataset"],
    )


def _observation(version: str, mode: str, protocol: str, surface: PublicSurface) -> ProtocolObservation:
    return ProtocolObservation(
        server_version=version,
        observed_server_version=version,
        client_mode=mode,
        expected_protocol=protocol,
        negotiated_protocol=protocol,
        surface=surface,
    )


def _artifact() -> ArtifactContinuity:
    return ArtifactContinuity(
        manifest_readable=True,
        manifest_run_id_matches=True,
        contact_sheet_readable=True,
        content_unchanged=True,
        contact_sheet_sha256="a" * 64,
    )


def _report(
    *,
    old_surface: PublicSurface | None = None,
    new_surface: PublicSurface | None = None,
    artifact: ArtifactContinuity | None = None,
) -> dict[str, Any]:
    old = old_surface or _surface()
    new = new_surface or _surface(extra_tool="trace_preview_variant")
    return build_upgrade_proof_report(
        package="albumentationsx-mcp",
        from_version="1.20.0",
        to_version="1.21.0",
        observed_on="2026-08-03",
        from_legacy=_observation("1.20.0", "legacy", "2025-11-25", old),
        to_legacy=_observation("1.21.0", "legacy", "2025-11-25", new),
        to_modern=_observation("1.21.0", "2026-07-28", "2026-07-28", new),
        artifact=artifact or _artifact(),
    )


def test_additive_upgrade_passes_without_emitting_public_identifier_lists() -> None:
    report = _report()
    encoded = json.dumps(report, sort_keys=True)

    assert report["status"] == "pass"
    assert report["failures"] == []
    assert report["compatibility"]["old_surface_is_subset"] is True
    assert "trace_preview_variant" not in encoded
    assert "/Users/" not in encoded
    assert "/home/" not in encoded


@pytest.mark.parametrize("category", ["tools", "resources", "resource_templates", "prompts"])
def test_removed_public_identifier_fails_closed(category: str) -> None:
    old = _surface()
    values = {name: list(items) for name, items in old.categories().items()}
    removed = values[category].pop()
    new = PublicSurface.build(
        tools=values["tools"],
        resources=values["resources"],
        resource_templates=values["resource_templates"],
        prompts=values["prompts"],
    )

    report = _report(old_surface=old, new_surface=new)

    assert report["status"] == "fail"
    assert report["compatibility"]["categories"][category]["missing"] == [removed]
    assert "surface_removed" in {failure["code"] for failure in report["failures"]}


def test_version_protocol_or_artifact_failure_is_reported_with_remediation() -> None:
    report = _report()
    old_row = _observation("1.20.0", "legacy", "2025-11-25", _surface())
    bad_protocol = replace(
        old_row,
        observed_server_version="9.9.9",
        negotiated_protocol="2026-07-28",
    )
    bad_artifact = replace(_artifact(), content_unchanged=False)

    failed = build_upgrade_proof_report(
        package="albumentationsx-mcp",
        from_version="1.20.0",
        to_version="1.21.0",
        observed_on="2026-08-03",
        from_legacy=bad_protocol,
        to_legacy=_observation("1.21.0", "legacy", "2025-11-25", _surface()),
        to_modern=_observation("1.21.0", "2026-07-28", "2026-07-28", _surface()),
        artifact=bad_artifact,
    )

    assert report["status"] == "pass"
    assert failed["status"] == "fail"
    assert {item["code"] for item in failed["failures"]} == {
        "artifact_continuity_failed",
        "protocol_negotiation_failed",
        "server_version_mismatch",
    }
    assert all(item["remediation"] for item in failed["failures"])


def test_report_is_deterministic_for_reordered_identifiers() -> None:
    first = _report()
    reordered = PublicSurface.build(
        tools=["search_transforms", "render_preview_batch"],
        resources=["albumentationsx://examples/client-smoke"],
        resource_templates=["albumentationsx://preview-artifacts/{run_id}/{filename}"],
        prompts=["augment_dataset"],
    )
    second = _report(old_surface=reordered)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
