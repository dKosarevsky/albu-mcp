from __future__ import annotations

from pathlib import Path

import pytest

from albumentationsx_mcp.lifecycle import build_lifecycle_status, render_lifecycle_status_markdown
from scripts.export_lifecycle_status import build_committed_lifecycle_status


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
    assert "Ready for v1" not in render_lifecycle_status_markdown(report)


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
    assert report["release_health"]["version"] == "1.19.0"
    assert [channel["id"] for channel in report["release_health"]["channels"]] == [
        "pypi",
        "github_release",
        "ci",
        "official_registry",
    ]
    assert report["host_evidence"]["status"] == "partial"
    assert report["adoption_experiment"]["campaign_id"] == "classification-robustness"


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
