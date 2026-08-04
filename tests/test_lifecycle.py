from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from albumentationsx_mcp.lifecycle import build_lifecycle_status, render_lifecycle_status_markdown
from scripts.export_lifecycle_status import build_committed_lifecycle_status

_PUBLISHED_UPGRADE_EVIDENCE = Path("docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-04.json")
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


def _protocol_compatibility() -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "passed",
        "status_basis": "Published upgrade probe result only; this does not assert provenance.",
        "from_version": "1.20.0",
        "to_version": "1.21.0",
        "evidence_path": "host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-04.json",
        "evidence_sha256": "2d6297cd017c118ecc690028fc0140052ea895d89140f32901531753ce3531da",
        "provenance": (
            "Local operator-run snapshot. No immutable public run or attestation is available; this evidence is not "
            "independently attested or provenance-verifiable."
        ),
        "scope": (
            "Streamable HTTP conformance and published-package artifact continuity. This is not real-host UI evidence."
        ),
    }


def _build_with_protocol(protocol: object) -> dict[str, Any]:
    return build_lifecycle_status(
        version="1.21.0",
        release_channels=_release_channels(),
        host_blockers=[],
        experiment=_experiment(),
        protocol_compatibility=cast("Any", protocol),
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


def test_lifecycle_protocol_compatibility_has_an_independent_schema_version() -> None:
    report = _build_with_protocol(_protocol_compatibility())

    assert report["schema_version"] == 1
    assert report["protocol_compatibility"]["schema_version"] == 1


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("extra", "unexpected"),
        ("missing", None),
        ("schema_version", True),
        ("status", "pass"),
        ("status", True),
        ("from_version", "1.20"),
        ("to_version", "v1.21.0"),
        ("unordered_versions", "1.19.0"),
        ("evidence_sha256", "A" * 64),
        ("evidence_sha256", "a" * 63),
        ("evidence_path", "javascript:alert.json"),
        ("evidence_path", "/tmp/evidence.json"),  # noqa: S108 - intentional rejected path.
        ("evidence_path", "../evidence.json"),
        ("evidence_path", "host-evidence/../../evidence.json"),
        ("evidence_path", "host-evidence/evidence.txt"),
        ("evidence_path", Path("host-evidence/evidence.json")),
        ("status_basis", "valid line\n## Injected heading"),
        ("provenance", 1),
    ],
)
def test_lifecycle_protocol_compatibility_rejects_invalid_schema(mutation: str, value: object) -> None:
    protocol = _protocol_compatibility()
    if mutation == "extra":
        protocol["unexpected"] = value
    elif mutation == "missing":
        del protocol["scope"]
    elif mutation == "unordered_versions":
        protocol["to_version"] = value
    else:
        protocol[mutation] = value

    with pytest.raises(ValueError, match=rf"^{_PROTOCOL_ERROR}$"):
        _build_with_protocol(protocol)


def test_lifecycle_protocol_compatibility_escapes_inline_markdown() -> None:
    protocol = _protocol_compatibility()
    protocol["status_basis"] = "# heading [link](javascript:alert(1)) `code`"
    protocol["provenance"] = "<script> *bold* _italic_ ![image](javascript:alert(1))"
    protocol["scope"] = r"backslash\pipe|heading#"

    rendered = render_lifecycle_status_markdown(_build_with_protocol(protocol))

    assert r"Status basis: \# heading \[link\](javascript:alert(1)) \`code\`" in rendered
    assert r"Provenance: \<script\> \*bold\* \_italic\_ \!\[image\](javascript:alert(1))" in rendered
    assert r"Scope: backslash\\pipe\|heading\#" in rendered
    assert "## Injected" not in rendered
    assert "[link](javascript:" not in rendered
    assert "`code`" not in rendered


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evidence_sha256", "not-a-digest"),
        ("evidence_path", "../../outside.json"),
        ("status", "failed"),
        ("scope", "safe\n## Mutated heading"),
        ("extra", "unexpected"),
    ],
)
def test_lifecycle_render_revalidates_mutated_protocol_data(field: str, value: str) -> None:
    report = _build_with_protocol(_protocol_compatibility())
    protocol = cast("dict[str, object]", report["protocol_compatibility"])
    protocol[field] = value

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

    assert report["release_health"]["status"] == "published"
    assert report["release_health"]["version"] == "1.21.0"
    assert [channel["id"] for channel in report["release_health"]["channels"]] == [
        "pypi",
        "github_release",
        "ci",
        "official_registry",
    ]
    assert report["host_evidence"]["status"] == "partial"
    assert report["adoption_experiment"]["campaign_id"] == "classification-robustness"
    assert report["protocol_compatibility"] == {
        "schema_version": 1,
        "status": "passed",
        "status_basis": "Published upgrade probe result only; this does not assert provenance.",
        "from_version": "1.20.0",
        "to_version": "1.21.0",
        "evidence_path": "host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-04.json",
        "evidence_sha256": "2d6297cd017c118ecc690028fc0140052ea895d89140f32901531753ce3531da",
        "provenance": (
            "Local operator-run snapshot. No immutable public run or attestation is available; this evidence is not "
            "independently attested or provenance-verifiable."
        ),
        "scope": (
            "Streamable HTTP conformance and published-package artifact continuity. This is not real-host UI evidence."
        ),
    }


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
    document_path = docs_root / "CUSTOM_STATUS.md"
    evidence_path.parent.mkdir(parents=True)
    raw_evidence = _PUBLISHED_UPGRADE_EVIDENCE.read_bytes()
    evidence_path.write_bytes(raw_evidence)

    report = build_committed_lifecycle_status(
        published_upgrade_path=evidence_path,
        docs_root=docs_root,
        document_path=document_path,
    )
    rendered = render_lifecycle_status_markdown(
        report,
        docs_root=docs_root,
        document_path=document_path,
    )

    assert report["protocol_compatibility"]["evidence_path"] == "proofs/custom-upgrade.json"
    assert report["protocol_compatibility"]["evidence_sha256"] == hashlib.sha256(raw_evidence).hexdigest()
    assert "Evidence: [privacy-safe machine report](proofs/custom-upgrade.json)" in rendered


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
    assert result.stderr == f"lifecycle status export error: {_COMMITTED_EVIDENCE_ERROR}\n"
    assert str(output_path) not in result.stderr
    assert not output_path.exists()


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
