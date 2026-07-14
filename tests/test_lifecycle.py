from __future__ import annotations

import pytest

from albumentationsx_mcp.lifecycle import build_lifecycle_status, render_lifecycle_status_markdown


def _experiment() -> dict[str, object]:
    return {
        "campaign_id": "classification-robustness",
        "status": "measuring",
        "baseline_date": "2026-07-14",
        "measurement_due": "2026-07-21",
        "post_url": None,
        "success_signal": "One voluntary render -> reject -> adjust -> accept report.",
    }


def test_lifecycle_status_keeps_release_host_and_adoption_independent() -> None:
    report = build_lifecycle_status(
        version="1.19.0",
        release_channels=[
            {"id": "pypi", "status": "published", "url": "https://pypi.org/project/albumentationsx-mcp/"},
            {"id": "github_release", "status": "published", "url": "https://example.test/releases/v1.19.0"},
            {"id": "official_registry", "status": "listed", "url": "https://example.test/registry"},
        ],
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
            release_channels=[{"id": "pypi", "status": "published", "url": "https://example.test"}],
            host_blockers=[],
            experiment=experiment,
        )
