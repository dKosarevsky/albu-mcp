from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import replace
from typing import Any, cast

import pytest

from albumentationsx_mcp.upgrade_proof import (
    ArtifactContinuity,
    ProtocolObservation,
    ProtocolSummary,
    PublicSurface,
    UpgradeProofReport,
    build_upgrade_proof_report,
)

_CATEGORIES = ("tools", "resources", "resource_templates", "prompts")
_ROLES = ("from_legacy", "to_legacy", "to_modern")


def _surface(
    *,
    tools: Iterable[str] | None = None,
    resources: Iterable[str] | None = None,
    resource_templates: Iterable[str] | None = None,
    prompts: Iterable[str] | None = None,
    extra_tool: str | None = None,
) -> PublicSurface:
    tool_values = list(tools) if tools is not None else ["render_preview_batch", "search_transforms"]
    if extra_tool is not None:
        tool_values.append(extra_tool)
    return PublicSurface.build(
        tools=tool_values,
        resources=resources if resources is not None else ["albumentationsx://examples/client-smoke"],
        resource_templates=(
            resource_templates
            if resource_templates is not None
            else ["albumentationsx://preview-artifacts/{run_id}/{filename}"]
        ),
        prompts=prompts if prompts is not None else ["augment_dataset"],
    )


def _surface_with_category(category: str, identifiers: Iterable[str]) -> PublicSurface:
    values = {name: list(items) for name, items in _surface().categories().items()}
    values[category] = list(identifiers)
    return PublicSurface.build(
        tools=values["tools"],
        resources=values["resources"],
        resource_templates=values["resource_templates"],
        prompts=values["prompts"],
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


def _evidence() -> dict[str, Any]:
    old = _surface()
    new = _surface(extra_tool="trace_preview_variant")
    return {
        "package": "albumentationsx-mcp",
        "from_version": "1.20.0",
        "to_version": "1.21.0",
        "observed_on": "2026-08-03",
        "from_legacy": _observation("1.20.0", "legacy", "2025-11-25", old),
        "to_legacy": _observation("1.21.0", "legacy", "2025-11-25", new),
        "to_modern": _observation("1.21.0", "2026-07-28", "2026-07-28", new),
        "artifact": _artifact(),
    }


def _report(**overrides: Any) -> UpgradeProofReport:
    evidence = _evidence()
    evidence.update(overrides)
    return build_upgrade_proof_report(**evidence)


def _report_for_surfaces(
    old: PublicSurface,
    new: PublicSurface,
    modern: PublicSurface | None = None,
) -> UpgradeProofReport:
    return _report(
        from_legacy=_observation("1.20.0", "legacy", "2025-11-25", old),
        to_legacy=_observation("1.21.0", "legacy", "2025-11-25", new),
        to_modern=_observation("1.21.0", "2026-07-28", "2026-07-28", modern or new),
    )


def _matrix_row(report: UpgradeProofReport, role: str) -> ProtocolSummary:
    return next(row for row in report["matrix"] if row["role"] == role)


def _expected_digest(*values: str) -> str:
    payload = json.dumps(sorted(set(values)), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_additive_upgrade_passes_without_emitting_public_identifier_lists() -> None:
    report = _report()
    encoded = json.dumps(report, sort_keys=True)

    assert report["status"] == "pass"
    assert report["failures"] == []
    assert report["compatibility"]["old_surface_is_subset"] is True
    assert "trace_preview_variant" not in encoded
    assert "render_preview_batch" not in encoded
    assert "/Users/" not in encoded
    assert "/home/" not in encoded


def test_report_has_exact_schema_shape() -> None:
    report = _report()

    assert set(report) == {
        "schema_version",
        "package",
        "from_version",
        "to_version",
        "observed_on",
        "status",
        "matrix",
        "compatibility",
        "artifact_continuity",
        "failures",
    }
    assert [row["role"] for row in report["matrix"]] == list(_ROLES)
    assert all(
        set(row)
        == {
            "role",
            "server_version",
            "observed_server_version",
            "client_mode",
            "expected_protocol",
            "negotiated_protocol",
            "server_version_ok",
            "protocol_ok",
            "ok",
            "surface",
        }
        for row in report["matrix"]
    )
    assert all(set(row["surface"]) == set(_CATEGORIES) for row in report["matrix"])
    assert all(
        set(summary) == {"count", "sha256"}
        for row in report["matrix"]
        for summary in cast("dict[str, dict[str, Any]]", row["surface"]).values()
    )

    compatibility = report["compatibility"]
    categories = cast("dict[str, dict[str, Any]]", compatibility["categories"])
    assert set(compatibility) == {"old_surface_is_subset", "new_modes_equal", "categories"}
    assert set(categories) == set(_CATEGORIES)
    assert all(
        set(category) == {"ok", "old", "new", "missing_count", "missing_sha256"} for category in categories.values()
    )
    assert all(
        set(summary) == {"count", "sha256"}
        for category in categories.values()
        for summary in (category["old"], category["new"])
    )
    assert set(report["artifact_continuity"]) == {
        "ok",
        "manifest_readable",
        "manifest_run_id_matches",
        "contact_sheet_readable",
        "content_unchanged",
        "contact_sheet_sha256",
    }


@pytest.mark.parametrize(
    ("role", "mismatch", "failure_code", "expected_checks"),
    [
        ("from_legacy", "observed_version", "server_version_mismatch", (False, True)),
        ("to_legacy", "observed_version", "server_version_mismatch", (False, True)),
        ("to_modern", "observed_version", "server_version_mismatch", (False, True)),
        ("from_legacy", "protocol", "protocol_negotiation_failed", (True, False)),
        ("to_legacy", "protocol", "protocol_negotiation_failed", (True, False)),
        ("to_modern", "protocol", "protocol_negotiation_failed", (True, False)),
    ],
)
def test_every_matrix_row_reports_version_and_protocol_mismatches(
    role: str,
    mismatch: str,
    failure_code: str,
    expected_checks: tuple[bool, bool],
) -> None:
    row = cast("ProtocolObservation", _evidence()[role])
    if mismatch == "observed_version":
        row = replace(row, observed_server_version="9.9.9")
    else:
        row = replace(row, negotiated_protocol="2099-01-01")

    report = _report(**{role: row})
    summary = _matrix_row(report, role)

    assert report["status"] == "fail"
    assert (summary["server_version_ok"], summary["protocol_ok"]) == expected_checks
    assert summary["ok"] is False
    assert (failure_code, role) in {(failure["code"], failure["scope"]) for failure in report["failures"]}


@pytest.mark.parametrize("role", _ROLES)
def test_matrix_role_version_must_match_report_version(role: str) -> None:
    row = cast("ProtocolObservation", _evidence()[role])
    row = replace(row, server_version="9.9.9", observed_server_version="9.9.9")

    report = _report(**{role: row})
    summary = _matrix_row(report, role)

    assert summary["server_version_ok"] is False
    assert summary["ok"] is False
    assert ("row_version_mismatch", role) in {(failure["code"], failure["scope"]) for failure in report["failures"]}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("server_version", ""),
        ("server_version", "x" * 129),
        ("observed_server_version", ""),
        ("observed_server_version", "x" * 129),
        ("client_mode", ""),
        ("client_mode", "x" * 129),
        ("expected_protocol", ""),
        ("expected_protocol", "x" * 129),
        ("negotiated_protocol", ""),
        ("negotiated_protocol", "x" * 129),
        ("client_mode", cast("Any", None)),
    ],
)
def test_malformed_observations_are_aggregated_and_sanitized(field: str, value: Any) -> None:
    row = replace(cast("ProtocolObservation", _evidence()["from_legacy"]), **{field: value})

    report = _report(from_legacy=row)
    summary = cast("dict[str, Any]", _matrix_row(report, "from_legacy"))
    encoded = json.dumps(report, sort_keys=True)

    assert report["status"] == "fail"
    assert summary[field] is None
    assert summary["ok"] is False
    assert ("observation_invalid", f"from_legacy.{field}") in {
        (failure["code"], failure["scope"]) for failure in report["failures"]
    }
    if isinstance(value, str) and value:
        assert value not in encoded


def test_observation_bound_is_measured_in_utf8_bytes() -> None:
    value = "\u00e9" * 65
    row = replace(cast("ProtocolObservation", _evidence()["from_legacy"]), client_mode=value)

    report = _report(from_legacy=row)

    assert _matrix_row(report, "from_legacy")["client_mode"] is None
    assert ("observation_invalid", "from_legacy.client_mode") in {
        (failure["code"], failure["scope"]) for failure in report["failures"]
    }


@pytest.mark.parametrize(
    ("field", "value", "failure_code"),
    [
        ("package", "", "package_invalid"),
        ("package", "x" * 129, "package_invalid"),
        ("from_version", "", "version_invalid"),
        ("from_version", "x" * 129, "version_invalid"),
        ("to_version", "", "version_invalid"),
        ("to_version", "x" * 129, "version_invalid"),
    ],
)
def test_invalid_report_metadata_is_aggregated_and_sanitized(
    field: str,
    value: str,
    failure_code: str,
) -> None:
    report = _report(**{field: value})
    encoded = json.dumps(report, sort_keys=True)

    assert report["status"] == "fail"
    assert cast("dict[str, Any]", report)[field] is None
    assert (failure_code, field) in {(failure["code"], failure["scope"]) for failure in report["failures"]}
    if value:
        assert value not in encoded


@pytest.mark.parametrize("observed_on", ["", "20260803", "2026-02-30", "2026-8-3", "x" * 129])
def test_observed_on_must_be_an_iso_calendar_date(observed_on: str) -> None:
    report = _report(observed_on=observed_on)

    assert report["status"] == "fail"
    assert report["observed_on"] is None
    assert ("observed_on_invalid", "observed_on") in {
        (failure["code"], failure["scope"]) for failure in report["failures"]
    }


def test_valid_iso_leap_day_is_preserved() -> None:
    report = _report(observed_on="2028-02-29")

    assert report["status"] == "pass"
    assert report["observed_on"] == "2028-02-29"


@pytest.mark.parametrize("category", _CATEGORIES)
def test_removed_public_identifier_uses_bounded_privacy_safe_evidence(category: str) -> None:
    sensitive = "/Users/private/builds/client-secret"
    retained = f"public-{category}"
    old = _surface_with_category(category, [retained, sensitive])
    new = _surface_with_category(category, [retained])

    report = _report_for_surfaces(old, new)
    categories = cast("dict[str, Any]", report["compatibility"]["categories"])
    category_report = cast("dict[str, Any]", categories[category])
    failure = next(
        item for item in report["failures"] if item["code"] == "surface_removed" and item["scope"] == category
    )
    encoded = json.dumps(report, sort_keys=True)

    assert report["status"] == "fail"
    assert category_report["missing_count"] == 1
    assert category_report["missing_sha256"] == _expected_digest(sensitive)
    assert set(failure) == {"code", "scope", "missing_count", "missing_sha256", "remediation"}
    assert failure["missing_count"] == 1
    assert failure["missing_sha256"] == _expected_digest(sensitive)
    assert sensitive not in encoded
    assert "/Users/" not in encoded
    assert "client-secret" not in encoded
    assert '"missing"' not in encoded


def test_surface_hash_uses_canonical_json_serialization() -> None:
    surface = _surface(tools=["a", "b,c"], resources=[], resource_templates=[], prompts=[])

    report = _report_for_surfaces(surface, surface)
    digest = _matrix_row(report, "from_legacy")["surface"]["tools"]["sha256"]

    assert digest == _expected_digest("a", "b,c")


def test_canonical_serialization_distinguishes_delimiter_collision_candidates() -> None:
    first = _surface(tools=["a", "b,c"], resources=[], resource_templates=[], prompts=[])
    second = _surface(tools=["a,b", "c"], resources=[], resource_templates=[], prompts=[])

    first_hash = _matrix_row(_report_for_surfaces(first, first), "from_legacy")["surface"]["tools"]["sha256"]
    second_hash = _matrix_row(_report_for_surfaces(second, second), "from_legacy")["surface"]["tools"]["sha256"]

    assert first_hash != second_hash


@pytest.mark.parametrize("identifier", ["line\nfeed", "null\x00byte", "delete\x7fbyte", "c1\x85byte"])
def test_public_identifiers_reject_control_characters(identifier: str) -> None:
    with pytest.raises(ValueError, match="control characters"):
        _surface(tools=[identifier])


def test_newline_join_collision_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="control characters"):
        _surface(tools=["a", "b\nc"])
    with pytest.raises(ValueError, match="control characters"):
        _surface(tools=["a\nb", "c"])


def test_public_surface_uses_documented_set_semantics() -> None:
    duplicated = PublicSurface.build(
        tools=["b", "a", "a"],
        resources=["resource", "resource"],
        resource_templates=[],
        prompts=["prompt", "prompt"],
    )
    unique = PublicSurface.build(
        tools=["a", "b"],
        resources=["resource"],
        resource_templates=[],
        prompts=["prompt"],
    )

    assert duplicated == unique
    assert duplicated.tools == ("a", "b")
    assert json.dumps(_report_for_surfaces(duplicated, duplicated), sort_keys=True) == json.dumps(
        _report_for_surfaces(unique, unique),
        sort_keys=True,
    )


def test_direct_public_surface_construction_cannot_bypass_canonicalization() -> None:
    direct = PublicSurface(
        tools=cast("Any", ["b", "a", "a"]),
        resources=cast("Any", ["resource", "resource"]),
        resource_templates=cast("Any", []),
        prompts=cast("Any", ["prompt", "prompt"]),
    )

    assert direct.tools == ("a", "b")
    assert direct.resources == ("resource",)
    assert direct.resource_templates == ()
    assert direct.prompts == ("prompt",)


@pytest.mark.parametrize("category", _CATEGORIES)
@pytest.mark.parametrize("constructor", ["build", "direct"])
def test_plain_string_is_rejected_as_identifier_iterable(category: str, constructor: str) -> None:
    values: dict[str, Any] = dict.fromkeys(_CATEGORIES, ())
    values[category] = "not-an-identifier-collection"
    factory: Any = PublicSurface.build if constructor == "build" else PublicSurface

    with pytest.raises(TypeError, match="plain string"):
        factory(**values)


def test_empty_categories_are_valid_sets_with_stable_hashes() -> None:
    empty = _surface(tools=[], resources=[], resource_templates=[], prompts=[])

    report = _report_for_surfaces(empty, empty)
    empty_digest = _expected_digest()

    assert report["status"] == "pass"
    assert empty.categories() == dict.fromkeys(_CATEGORIES, ())
    categories = cast("dict[str, dict[str, Any]]", report["compatibility"]["categories"])
    for category in categories.values():
        assert category["ok"] is True
        assert category["missing_count"] == 0
        assert category["missing_sha256"] == empty_digest
        assert category["old"] == {"count": 0, "sha256": empty_digest}
        assert category["new"] == {"count": 0, "sha256": empty_digest}


@pytest.mark.parametrize(
    "field",
    ["manifest_readable", "manifest_run_id_matches", "contact_sheet_readable", "content_unchanged"],
)
def test_each_artifact_boolean_failure_is_reported(field: str) -> None:
    artifact = replace(_artifact(), **{field: False})

    report = _report(artifact=artifact)
    artifact_report = cast("dict[str, Any]", report["artifact_continuity"])

    assert report["status"] == "fail"
    assert artifact_report["ok"] is False
    assert artifact_report[field] is False
    assert ("artifact_continuity_failed", field) in {
        (failure["code"], failure["scope"]) for failure in report["failures"]
    }


@pytest.mark.parametrize("digest", ["", "a" * 63, "A" * 64, "g" * 64])
def test_artifact_hash_must_be_lowercase_64_hex(digest: str) -> None:
    report = _report(artifact=replace(_artifact(), contact_sheet_sha256=digest))
    encoded = json.dumps(report, sort_keys=True)

    assert report["status"] == "fail"
    assert report["artifact_continuity"]["ok"] is False
    assert report["artifact_continuity"]["contact_sheet_sha256"] is None
    assert ("artifact_sha256_invalid", "contact_sheet_sha256") in {
        (failure["code"], failure["scope"]) for failure in report["failures"]
    }
    if digest:
        assert digest not in encoded


def test_all_validation_failures_are_aggregated_without_raising() -> None:
    malformed = ProtocolObservation(
        server_version="",
        observed_server_version="",
        client_mode="",
        expected_protocol="",
        negotiated_protocol="",
        surface=_surface(),
    )
    artifact = ArtifactContinuity(
        manifest_readable=False,
        manifest_run_id_matches=False,
        contact_sheet_readable=False,
        content_unchanged=False,
        contact_sheet_sha256="INVALID",
    )

    report = _report(observed_on="not-a-date", from_legacy=malformed, artifact=artifact)
    summary = _matrix_row(report, "from_legacy")

    assert report["status"] == "fail"
    assert len(report["failures"]) == 11
    assert all(failure["remediation"] for failure in report["failures"])
    assert summary["server_version"] is None
    assert summary["observed_server_version"] is None
    assert summary["client_mode"] is None
    assert summary["expected_protocol"] is None
    assert summary["negotiated_protocol"] is None


def test_failure_order_is_stable_and_deterministic() -> None:
    old = _surface(
        tools=["tool-retained", "tool-removed"],
        resources=["resource-retained", "resource-removed"],
        resource_templates=[],
        prompts=[],
    )
    new = _surface(
        tools=["tool-retained"],
        resources=["resource-retained"],
        resource_templates=[],
        prompts=[],
    )
    modern = _surface(
        tools=["modern-only", "tool-retained"],
        resources=["resource-retained"],
        resource_templates=[],
        prompts=[],
    )
    bad_from = replace(
        _observation("1.20.0", "legacy", "2025-11-25", old),
        observed_server_version="9.9.9",
        negotiated_protocol="2099-01-01",
    )
    artifact = replace(
        _artifact(),
        manifest_readable=False,
        contact_sheet_readable=False,
        contact_sheet_sha256="A" * 64,
    )

    report = _report(
        observed_on="2026-02-30",
        from_legacy=bad_from,
        to_legacy=_observation("1.21.0", "legacy", "2025-11-25", new),
        to_modern=_observation("1.21.0", "2026-07-28", "2026-07-28", modern),
        artifact=artifact,
    )

    assert [(failure["code"], failure["scope"]) for failure in report["failures"]] == [
        ("observed_on_invalid", "observed_on"),
        ("server_version_mismatch", "from_legacy"),
        ("protocol_negotiation_failed", "from_legacy"),
        ("surface_removed", "tools"),
        ("surface_removed", "resources"),
        ("new_mode_surface_mismatch", "to_version"),
        ("artifact_continuity_failed", "manifest_readable"),
        ("artifact_continuity_failed", "contact_sheet_readable"),
        ("artifact_sha256_invalid", "contact_sheet_sha256"),
    ]
    assert all(
        set(failure) == {"code", "scope", "missing_count", "missing_sha256", "remediation"}
        for failure in report["failures"]
    )


def test_report_is_deterministic_for_reordered_and_duplicate_identifiers() -> None:
    first = _report()
    reordered = PublicSurface.build(
        tools=["search_transforms", "render_preview_batch", "search_transforms"],
        resources=["albumentationsx://examples/client-smoke"],
        resource_templates=["albumentationsx://preview-artifacts/{run_id}/{filename}"],
        prompts=["augment_dataset"],
    )
    second = _report(
        from_legacy=_observation("1.20.0", "legacy", "2025-11-25", reordered),
    )

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
