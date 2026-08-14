from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

import scripts.export_lifecycle_status as lifecycle_export
from albumentationsx_mcp.lifecycle import (
    ProtocolCompatibilityEvidence,
    PublishedUpgradeExpectation,
    build_lifecycle_status,
    load_protocol_compatibility_evidence,
    render_lifecycle_status_markdown,
)
from albumentationsx_mcp.published_provenance import (
    build_published_upgrade_provenance,
    serialize_published_upgrade_provenance,
)
from scripts.export_lifecycle_status import build_committed_lifecycle_status

_PUBLISHED_UPGRADE_EVIDENCE = Path("docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-05.json")
_PROTOCOL_ERROR = "protocol compatibility evidence is invalid"
_COMMITTED_EVIDENCE_ERROR = "published upgrade evidence is invalid"


def _experiment() -> dict[str, object]:
    return {
        "campaign_id": "classification-robustness",
        "status": "measuring",
        "baseline_date": "2026-07-14",
        "measurement_due": "2026-07-21",
        "post_url": None,
        "success_signal": "One voluntary render -> reject -> adjust -> accept report.",
    }


def _release_channels() -> list[dict[str, str]]:
    return [
        {"id": "pypi", "status": "published", "url": "https://pypi.org/project/albumentationsx-mcp/"},
        {"id": "github_release", "status": "published", "url": "https://example.test/releases/v1.19.0"},
        {"id": "ci", "status": "passed", "url": "https://example.test/actions/runs/1"},
        {"id": "official_registry", "status": "listed", "url": "https://example.test/registry"},
    ]


def _forged_protocol_mapping() -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "passed",
        "status_basis": "Passing published upgrade probe; provenance and scope are reported separately.",
        "from_version": "1.20.0",
        "to_version": "1.21.0",
        "evidence_path": "host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-04.json",
        "evidence_sha256": "2d6297cd017c118ecc690028fc0140052ea895d89140f32901531753ce3531da",
        "provenance": (
            "Local operator-run snapshot. No immutable public run or attestation is available; this evidence is not "
            "independently attested or provenance-verifiable."
        ),
        "scope": (
            "Published-package stdio protocol negotiation and artifact continuity. "
            "This is not Streamable HTTP or real-host UI evidence."
        ),
    }


def _load_protocol_evidence(
    docs_root: Path,
    *,
    evidence_relative: str = "proofs/proof.json",
    document_relative: str = "STATUS.md",
    public_provenance: bool = False,
) -> tuple[ProtocolCompatibilityEvidence, Path, Path]:
    evidence_path = docs_root / evidence_relative
    document_path = docs_root / document_relative
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    document_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_bytes(_PUBLISHED_UPGRADE_EVIDENCE.read_bytes())
    provenance_path = None
    if public_provenance:
        provenance_path = evidence_path.with_name(f"{evidence_path.stem}.provenance.json")
        provenance = build_published_upgrade_provenance(
            evidence=evidence_path.read_bytes(),
            repository="dKosarevsky/albu-mcp",
            workflow_path=".github/workflows/published-upgrade-proof.yml",
            workflow_ref=("dKosarevsky/albu-mcp/.github/workflows/published-upgrade-proof.yml@refs/heads/main"),
            run_id=31_049_485_055,
            run_head_sha="8e185cb32a895a31fe3264b313372058fbfcea49",
            artifact_name="published-upgrade-proof",
            artifact_file="published-upgrade-proof.json",
            artifact_retention_days=30,
            verified_on="2026-08-05",
            verification_method="downloaded_artifact",
        )
        provenance_path.write_text(serialize_published_upgrade_provenance(provenance), encoding="utf-8")
    evidence = load_protocol_compatibility_evidence(
        evidence_path=evidence_path,
        provenance_path=provenance_path,
        trusted_root=docs_root,
        document_path=document_path,
        expectation=PublishedUpgradeExpectation(
            from_version="1.20.0",
            to_version="1.21.0",
            observed_on="2026-08-05",
        ),
    )
    return evidence, evidence_path, document_path


def _build_with_protocol(protocol: object, *, version: str = "1.21.0") -> dict[str, Any]:
    return build_lifecycle_status(
        version=version,
        release_channels=_release_channels(),
        host_blockers=[],
        experiment=_experiment(),
        protocol_compatibility=protocol,  # ty: ignore[invalid-argument-type] - runtime boundary test.
    )


def test_lifecycle_status_keeps_release_host_and_adoption_independent() -> None:
    report = build_lifecycle_status(
        version="1.19.0",
        release_channels=_release_channels(),
        host_blockers=[{"code": "manual_host_ui_pending", "summary": "Claude Code was not observed."}],
        experiment=_experiment(),
    )

    assert report["release_health"]["status"] == "published"
    assert report["host_evidence"] == {
        "status": "partial",
        "unresolved_count": 1,
        "blockers": [{"code": "manual_host_ui_pending", "summary": "Claude Code was not observed."}],
    }
    assert report["adoption_experiment"]["status"] == "measuring"
    rendered = render_lifecycle_status_markdown(report)
    assert "Ready for v1" not in rendered
    assert "Protocol Compatibility Evidence" not in rendered
    assert report["schema_version"] == 1


def test_lifecycle_rejects_direct_forged_protocol_mapping() -> None:
    forged = _forged_protocol_mapping()

    with pytest.raises(ValueError, match=rf"^{_PROTOCOL_ERROR}$"):
        _build_with_protocol(forged)

    report = _build_with_protocol(None)
    report["protocol_compatibility"] = forged
    with pytest.raises(ValueError, match=rf"^{_PROTOCOL_ERROR}$"):
        render_lifecycle_status_markdown(report)


def test_protocol_evidence_factory_derives_immutable_claim_from_canonical_file(tmp_path: Path) -> None:
    evidence, evidence_path, _document_path = _load_protocol_evidence(tmp_path / "docs")

    assert evidence.schema_version == 1
    assert evidence.status == "passed"
    assert evidence.from_version == "1.20.0"
    assert evidence.to_version == "1.21.0"
    assert evidence.evidence_sha256 == hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    assert evidence.evidence_href == "proofs/proof.json"
    with pytest.raises(TypeError):
        ProtocolCompatibilityEvidence()
    with pytest.raises(FrozenInstanceError):
        evidence.evidence_sha256 = "0" * 64  # ty: ignore[invalid-assignment]


def test_protocol_evidence_binds_public_run_without_claiming_attestation(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    evidence, _evidence_path, _document_path = _load_protocol_evidence(docs_root, public_provenance=True)
    rendered = render_lifecycle_status_markdown(_build_with_protocol(evidence))

    assert evidence.public_run_url == "https://github.com/dKosarevsky/albu-mcp/actions/runs/31049485055"
    assert evidence.public_run_head_sha == "8e185cb32a895a31fe3264b313372058fbfcea49"
    assert evidence.provenance_href == "proofs/proof.provenance.json"
    assert evidence.artifact_retention_days == 30
    assert evidence.verification_method == "downloaded_artifact"
    assert "[public GitHub Actions run](https://github.com/dKosarevsky/albu-mcp/actions/runs/31049485055)" in rendered
    assert "Artifact retention: `30 days`" in rendered
    assert "This is not cryptographic attestation." in rendered


def test_protocol_evidence_rejects_public_provenance_file_change(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    evidence, evidence_path, _document_path = _load_protocol_evidence(docs_root, public_provenance=True)
    report = _build_with_protocol(evidence)
    provenance_path = evidence_path.with_name(f"{evidence_path.stem}.provenance.json")
    provenance_path.write_bytes(provenance_path.read_bytes() + b"\n")

    with pytest.raises(ValueError, match=rf"^{_PROTOCOL_ERROR}$"):
        render_lifecycle_status_markdown(report)


def test_protocol_evidence_rejects_public_provenance_for_different_evidence(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    evidence_path = docs_root / "proof.json"
    provenance_path = docs_root / "proof.provenance.json"
    docs_root.mkdir()
    evidence_path.write_bytes(_PUBLISHED_UPGRADE_EVIDENCE.read_bytes())
    provenance = build_published_upgrade_provenance(
        evidence=b"different evidence",
        repository="dKosarevsky/albu-mcp",
        workflow_path=".github/workflows/published-upgrade-proof.yml",
        workflow_ref="dKosarevsky/albu-mcp/.github/workflows/published-upgrade-proof.yml@refs/heads/main",
        run_id=31_049_485_055,
        run_head_sha="8e185cb32a895a31fe3264b313372058fbfcea49",
        artifact_name="published-upgrade-proof",
        artifact_file="published-upgrade-proof.json",
        artifact_retention_days=30,
        verified_on="2026-08-05",
        verification_method="downloaded_artifact",
    )
    provenance_path.write_text(serialize_published_upgrade_provenance(provenance), encoding="utf-8")

    with pytest.raises(ValueError, match=rf"^{_PROTOCOL_ERROR}$"):
        load_protocol_compatibility_evidence(
            evidence_path=evidence_path,
            provenance_path=provenance_path,
            trusted_root=docs_root,
            document_path=docs_root / "STATUS.md",
            expectation=PublishedUpgradeExpectation(
                from_version="1.20.0",
                to_version="1.21.0",
                observed_on="2026-08-05",
            ),
        )


def test_rendered_protocol_scope_is_explicitly_stdio_only(tmp_path: Path) -> None:
    evidence, _evidence_path, _document_path = _load_protocol_evidence(tmp_path / "docs")
    rendered = render_lifecycle_status_markdown(_build_with_protocol(evidence))
    start = rendered.index("## Protocol Compatibility Evidence")
    end = rendered.index("\n## Host Evidence", start)
    protocol_section = rendered[start:end]

    assert (
        "Scope: Published-package stdio protocol negotiation and artifact continuity. "
        "This is not Streamable HTTP or real-host UI evidence."
    ) in protocol_section
    assert "Streamable HTTP conformance" not in protocol_section


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evidence_sha256", "0" * 64),
        ("to_version", "1.22.0"),
    ],
)
def test_lifecycle_render_rejects_low_level_tampering_with_trusted_evidence(
    field: str,
    value: object,
    tmp_path: Path,
) -> None:
    evidence, _evidence_path, _document_path = _load_protocol_evidence(tmp_path / "docs")
    report = _build_with_protocol(evidence)
    object.__setattr__(evidence, field, value)

    with pytest.raises(ValueError, match=rf"^{_PROTOCOL_ERROR}$"):
        render_lifecycle_status_markdown(report)


def test_lifecycle_render_rejects_low_level_path_tampering(tmp_path: Path) -> None:
    evidence, _evidence_path, _document_path = _load_protocol_evidence(tmp_path / "docs")
    report = _build_with_protocol(evidence)
    object.__setattr__(evidence.binding.path_context, "evidence_path", Path("missing-proof.json"))

    with pytest.raises(ValueError, match=rf"^{_PROTOCOL_ERROR}$"):
        render_lifecycle_status_markdown(report)


@pytest.mark.parametrize("change", ["content", "replacement"])
def test_lifecycle_render_rejects_evidence_file_change_or_replacement(change: str, tmp_path: Path) -> None:
    evidence, evidence_path, _document_path = _load_protocol_evidence(tmp_path / "docs")
    report = _build_with_protocol(evidence)
    if change == "content":
        evidence_path.write_bytes(evidence_path.read_bytes() + b"\n")
    else:
        replacement = evidence_path.with_name("replacement.json")
        replacement.write_bytes(evidence_path.read_bytes())
        replacement.replace(evidence_path)

    with pytest.raises(ValueError, match=rf"^{_PROTOCOL_ERROR}$"):
        render_lifecycle_status_markdown(report)


def test_lifecycle_reuses_protocol_evidence_only_within_the_same_patch_line(tmp_path: Path) -> None:
    evidence, _evidence_path, _document_path = _load_protocol_evidence(tmp_path / "docs")

    patch_report = _build_with_protocol(evidence, version="1.21.1")
    assert patch_report["protocol_compatibility"].to_version == "1.21.0"
    assert "Published upgrade: `1.20.0 -> 1.21.0`" in render_lifecycle_status_markdown(patch_report)

    with pytest.raises(ValueError, match=rf"^{_PROTOCOL_ERROR}$"):
        _build_with_protocol(evidence, version="1.22.0")

    report = _build_with_protocol(evidence)
    report["release_health"]["version"] = "1.22.0"  # type: ignore[index]
    with pytest.raises(ValueError, match=rf"^{_PROTOCOL_ERROR}$"):
        render_lifecycle_status_markdown(report)


def test_lifecycle_release_failure_takes_priority_over_unobserved_channel() -> None:
    channels = _release_channels()
    channels[2]["status"] = "failed"
    channels[3]["status"] = "unknown"

    report = build_lifecycle_status(
        version="1.19.0",
        release_channels=channels,
        host_blockers=[],
        experiment=_experiment(),
    )

    assert report["release_health"]["status"] == "attention_required"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("status", "unknown", "unsupported adoption experiment status"),
        ("measurement_due", "2026-07-13", "measurement_due must not precede baseline_date"),
    ],
)
def test_lifecycle_status_rejects_invalid_experiment(field: str, value: str, message: str) -> None:
    experiment = _experiment()
    experiment[field] = value

    with pytest.raises(ValueError, match=message):
        build_lifecycle_status(
            version="1.19.0",
            release_channels=_release_channels(),
            host_blockers=[],
            experiment=experiment,
        )


def test_committed_lifecycle_status_describes_current_project_state() -> None:
    report = build_committed_lifecycle_status()

    assert report["release_health"]["status"] == "unknown"
    assert report["release_health"]["version"] == "1.21.1"
    assert [channel["id"] for channel in report["release_health"]["channels"]] == [
        "pypi",
        "github_release",
        "ci",
        "official_registry",
    ]
    assert report["host_evidence"]["status"] == "partial"
    assert report["adoption_experiment"]["campaign_id"] == "classification-robustness"
    protocol = report["protocol_compatibility"]
    assert isinstance(protocol, ProtocolCompatibilityEvidence)
    assert protocol.schema_version == 1
    assert protocol.status == "passed"
    assert protocol.status_basis == "Passing published upgrade probe; provenance and scope are reported separately."
    assert protocol.from_version == "1.20.0"
    assert protocol.to_version == "1.21.0"
    assert protocol.evidence_href == "host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-05.json"
    assert protocol.evidence_sha256 == "42580ac9d9893b748cd10e38f73067402e5e3b639dee84a5efefbe706bcac18c"
    assert protocol.provenance == (
        "Exact report bytes verified from a downloaded public GitHub Actions artifact. "
        "This is not cryptographic attestation."
    )
    assert protocol.provenance_href == ("host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-05.provenance.json")
    assert protocol.public_run_url == "https://github.com/dKosarevsky/albu-mcp/actions/runs/31049485055"
    assert protocol.public_run_head_sha == "8e185cb32a895a31fe3264b313372058fbfcea49"
    assert protocol.artifact_retention_days == 30
    assert protocol.verification_method == "downloaded_artifact"
    assert protocol.scope == (
        "Published-package stdio protocol negotiation and artifact continuity. "
        "This is not Streamable HTTP or real-host UI evidence."
    )


@pytest.mark.parametrize("mutation", ["noncanonical", "mismatched"])
def test_committed_lifecycle_status_rejects_invalid_upgrade_evidence(mutation: str, tmp_path: Path) -> None:
    raw_evidence = _PUBLISHED_UPGRADE_EVIDENCE.read_bytes()
    if mutation == "noncanonical":
        mutated = raw_evidence + b"\n"
    else:
        report = json.loads(raw_evidence)
        report["to_version"] = "1.22.0"
        mutated = (json.dumps(report, allow_nan=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    evidence_path = docs_root / _PUBLISHED_UPGRADE_EVIDENCE.name
    evidence_path.write_bytes(mutated)

    with pytest.raises(ValueError, match=rf"^{_COMMITTED_EVIDENCE_ERROR}$"):
        build_committed_lifecycle_status(
            published_upgrade_path=evidence_path,
            docs_root=docs_root,
            document_path=docs_root / "STATUS.md",
        )


def test_committed_lifecycle_status_derives_link_from_actual_evidence_and_document(tmp_path: Path) -> None:
    docs_root = tmp_path / "project" / "docs"
    evidence_path = docs_root / "proofs" / "custom-upgrade.json"
    document_path = docs_root / "reports" / "CUSTOM_STATUS.md"
    evidence_path.parent.mkdir(parents=True)
    document_path.parent.mkdir()
    raw_evidence = _PUBLISHED_UPGRADE_EVIDENCE.read_bytes()
    evidence_path.write_bytes(raw_evidence)

    report = build_committed_lifecycle_status(
        published_upgrade_path=evidence_path,
        docs_root=docs_root,
        document_path=document_path,
    )
    rendered = render_lifecycle_status_markdown(report)

    protocol = report["protocol_compatibility"]
    assert isinstance(protocol, ProtocolCompatibilityEvidence)
    assert protocol.evidence_href == "../proofs/custom-upgrade.json"
    assert protocol.evidence_sha256 == hashlib.sha256(raw_evidence).hexdigest()
    assert "Evidence: [privacy-safe machine report](../proofs/custom-upgrade.json)" in rendered


@pytest.mark.parametrize("alias", ["exact", "symlink"])
def test_committed_lifecycle_status_rejects_document_evidence_alias(
    alias: str,
    tmp_path: Path,
) -> None:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    evidence_path = docs_root / "upgrade.json"
    evidence_path.write_bytes(_PUBLISHED_UPGRADE_EVIDENCE.read_bytes())
    document_path = evidence_path
    if alias == "symlink":
        document_path = docs_root / "STATUS.md"
        try:
            document_path.symlink_to(evidence_path)
        except OSError as error:
            pytest.skip(f"symlink creation unavailable: {error}")

    with pytest.raises(ValueError, match=rf"^{_COMMITTED_EVIDENCE_ERROR}$"):
        build_committed_lifecycle_status(
            published_upgrade_path=evidence_path,
            docs_root=docs_root,
            document_path=document_path,
        )


def test_committed_lifecycle_status_rejects_directory_document_path(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    evidence_path = docs_root / "upgrade.json"
    evidence_path.write_bytes(_PUBLISHED_UPGRADE_EVIDENCE.read_bytes())
    document_path = docs_root / "status-directory"
    document_path.mkdir()

    with pytest.raises(ValueError, match=rf"^{_COMMITTED_EVIDENCE_ERROR}$"):
        build_committed_lifecycle_status(
            published_upgrade_path=evidence_path,
            docs_root=docs_root,
            document_path=document_path,
        )


def test_committed_lifecycle_status_requires_existing_document_parent(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    evidence_path = docs_root / "upgrade.json"
    evidence_path.write_bytes(_PUBLISHED_UPGRADE_EVIDENCE.read_bytes())
    document_path = docs_root / "missing" / "STATUS.md"

    with pytest.raises(ValueError, match=rf"^{_COMMITTED_EVIDENCE_ERROR}$"):
        build_committed_lifecycle_status(
            published_upgrade_path=evidence_path,
            docs_root=docs_root,
            document_path=document_path,
        )

    assert not document_path.parent.exists()


@pytest.mark.parametrize("outside", ["evidence", "document"])
def test_committed_lifecycle_status_rejects_paths_outside_trusted_docs_root(outside: str, tmp_path: Path) -> None:
    docs_root = tmp_path / "project" / "docs"
    docs_root.mkdir(parents=True)
    inside_evidence = docs_root / "upgrade.json"
    outside_evidence = tmp_path / "outside" / "upgrade.json"
    outside_evidence.parent.mkdir()
    raw_evidence = _PUBLISHED_UPGRADE_EVIDENCE.read_bytes()
    inside_evidence.write_bytes(raw_evidence)
    outside_evidence.write_bytes(raw_evidence)
    evidence_path = outside_evidence if outside == "evidence" else inside_evidence
    document_path = tmp_path / "outside-status.md" if outside == "document" else docs_root / "STATUS.md"

    with pytest.raises(ValueError, match=rf"^{_COMMITTED_EVIDENCE_ERROR}$") as exc_info:
        build_committed_lifecycle_status(
            published_upgrade_path=evidence_path,
            docs_root=docs_root,
            document_path=document_path,
        )

    assert str(tmp_path) not in str(exc_info.value)


def test_committed_lifecycle_status_wraps_missing_evidence_without_path_leak(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    missing_path = docs_root / "private-operator-name.json"

    with pytest.raises(ValueError, match=rf"^{_COMMITTED_EVIDENCE_ERROR}$") as exc_info:
        build_committed_lifecycle_status(
            published_upgrade_path=missing_path,
            docs_root=docs_root,
            document_path=docs_root / "STATUS.md",
        )

    assert str(missing_path) not in str(exc_info.value)


def test_lifecycle_export_cli_rejects_output_outside_trusted_docs_root(tmp_path: Path) -> None:
    output_path = tmp_path / "private-operator-name.md"

    result = subprocess.run(  # noqa: S603 - fixed local script and controlled test path.
        [sys.executable, "scripts/export_lifecycle_status.py", "--output", str(output_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == "lifecycle status export failed\n"
    assert str(output_path) not in result.stderr
    assert not output_path.exists()


def test_lifecycle_export_cli_rejects_directory_output_without_traceback() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/export_lifecycle_status.py", "--output", "docs"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == "lifecycle status export failed\n"
    assert "Traceback" not in result.stderr


def test_lifecycle_export_delegates_to_atomic_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Path, str]] = []

    def record_write(path: Path, content: str) -> None:
        calls.append((path, content))

    monkeypatch.setattr(lifecycle_export, "write_atomic_text", record_write)
    monkeypatch.setattr(sys, "argv", ["export_lifecycle_status.py", "--output", "docs/STATUS.md"])

    lifecycle_export.main()

    assert calls == [(Path("docs/STATUS.md"), Path("docs/STATUS.md").read_text(encoding="utf-8"))]


def test_lifecycle_export_wraps_write_failure_without_partial_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = Path("docs/STATUS.md")
    original = output.read_bytes()
    sensitive_path = "/private/operator/build/status.md"

    def fail_write(_path: Path, _content: str) -> None:
        raise OSError(sensitive_path)

    monkeypatch.setattr(lifecycle_export, "write_atomic_text", fail_write)
    monkeypatch.setattr(sys, "argv", ["export_lifecycle_status.py", "--output", str(output)])

    with pytest.raises(SystemExit) as exc_info:
        lifecycle_export.main()

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "lifecycle status export failed\n"
    assert sensitive_path not in captured.err
    assert output.read_bytes() == original


def test_committed_lifecycle_status_does_not_infer_publication_without_evidence(tmp_path: Path) -> None:
    report = build_committed_lifecycle_status(release_health_path=tmp_path / "missing-release-health.json")

    assert report["release_health"]["status"] == "unknown"
    assert {channel["status"] for channel in report["release_health"]["channels"]} <= {
        "unknown",
        "not_observed",
    }


def test_committed_lifecycle_status_ignores_evidence_for_another_version(tmp_path: Path) -> None:
    evidence_path = tmp_path / "release-health.json"
    evidence_path.write_text(
        """{
  "schema_version": 1,
  "version": "0.0.1",
  "observed_at": "2026-07-14",
  "channels": []
}
""",
        encoding="utf-8",
    )

    report = build_committed_lifecycle_status(release_health_path=evidence_path)

    assert report["release_health"]["status"] == "unknown"


def test_committed_lifecycle_status_markdown_is_current() -> None:
    status_path = Path("docs/STATUS.md")

    assert status_path.read_text(encoding="utf-8") == render_lifecycle_status_markdown(
        build_committed_lifecycle_status()
    )
