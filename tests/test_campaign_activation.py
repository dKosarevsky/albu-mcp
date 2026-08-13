from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from albumentationsx_mcp.campaign_activation import (
    build_campaign_activation_report,
    render_campaign_activation_markdown,
)

FIXTURE_PATH = Path("tests/fixtures/campaign_activation_input.json")
PRIVATE_VALUES = {
    "alice-private-login",
    "bob-private-login",
    "charlie-private-login",
    "Private customer title",
    "Another private title",
    "/Users/alice/private/image.png",
    "https://example.invalid/issues/101",
}


def test_campaign_report_counts_only_completed_attributed_loops() -> None:
    report = build_campaign_activation_report(**_fixture())

    assert report["campaign"] == {
        "id": "classification-robustness",
        "starts_on": "2026-08-13",
        "ends_on": "2026-08-27",
        "as_of": "2026-08-20",
        "phase": "active",
        "destination_url": (
            "https://github.com/dKosarevsky/albu-mcp/blob/main/docs/use-cases/CLASSIFICATION_ROBUSTNESS.md"
        ),
    }
    assert report["activation"]["attributed_reports"] == 4
    assert report["activation"]["completed_loops"] == 3
    assert report["activation"]["distinct_submitters"] == 2
    assert report["activation"]["target_met"] is False
    assert report["privacy"] == {
        "runtime_telemetry": False,
        "reads_local_data": False,
        "contains_issue_level_data": False,
        "issue_data_usage": "aggregate voluntary public issue fields in memory only",
    }


def test_campaign_report_aggregates_bounded_sources_routes_and_outcomes() -> None:
    report = build_campaign_activation_report(**_fixture())

    assert report["activation"]["discovery_sources"] == {
        "albumentations-discord": 2,
        "github": 1,
        "x-twitter": 1,
    }
    assert report["activation"]["install_routes"] == {
        "claude-desktop-mcpb": 2,
        "uvx": 2,
    }
    assert report["activation"]["outcomes"] == {
        "accepted-after-adjustment": 3,
        "blocked-before-render": 1,
    }
    assert report["qualified_reach"]["current_unique_visitors"] == 12
    assert report["qualified_reach"]["target_met"] is False
    assert report["mcpb_conversion_proxy"]["incremental_downloads"] == 3
    assert report["mcpb_conversion_proxy"]["target_met"] is False


def test_campaign_report_never_returns_issue_level_values() -> None:
    report = build_campaign_activation_report(**_fixture())
    serialized = json.dumps(report, sort_keys=True)
    markdown = render_campaign_activation_markdown(report)

    for private_value in PRIVATE_VALUES:
        assert private_value not in serialized
        assert private_value not in markdown
    assert "Runtime telemetry: `disabled`" in markdown
    assert "Completed adjustment loops: `3`" in markdown
    assert "Distinct submitters: `2`" in markdown


@pytest.mark.parametrize(
    ("as_of", "expected_phase", "expected_recommendation"),
    [
        ("2026-08-12", "not_started", "continue"),
        ("2026-08-20", "active", "continue"),
        ("2026-08-27", "ended", "adjust"),
        ("2026-09-01", "ended", "adjust"),
    ],
)
def test_campaign_report_applies_bounded_decision_policy(
    as_of: str,
    expected_phase: str,
    expected_recommendation: str,
) -> None:
    payload = _fixture()
    payload["growth_report"]["as_of"] = as_of

    report = build_campaign_activation_report(**payload)

    assert report["campaign"]["phase"] == expected_phase
    assert report["recommendation"] == expected_recommendation


def test_campaign_report_continues_after_all_targets_are_met() -> None:
    payload = _fixture()
    payload["growth_report"]["as_of"] = "2026-08-28"
    payload["growth_report"]["github"]["unique_visitors"] = 20
    payload["growth_report"]["release_assets"]["mcpb_downloads_total"] = 27
    third_submitter = deepcopy(payload["workflow_feedback_issues"][1])
    third_submitter["id"] = 106
    third_submitter["user"] = {"login": "erin-private-login"}
    payload["workflow_feedback_issues"].append(third_submitter)

    report = build_campaign_activation_report(**payload)

    assert report["targets_met"] is True
    assert report["recommendation"] == "continue"


def test_campaign_report_stops_only_after_deadline_with_no_observed_movement() -> None:
    payload = _fixture()
    payload["growth_report"]["as_of"] = "2026-08-28"
    payload["growth_report"]["github"]["unique_visitors"] = 3
    payload["growth_report"]["release_assets"]["mcpb_downloads_total"] = 22
    payload["workflow_feedback_issues"] = []

    report = build_campaign_activation_report(**payload)

    assert report["recommendation"] == "stop"


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("config", "id"), "", "campaign id"),
        (("config", "ends_on"), "2026-08-26", "14 days"),
        (("config", "targets", "completed_loops"), -1, "non-negative"),
        (("growth_report", "release_assets", "mcpb_downloads_total"), -1, "non-negative"),
    ],
)
def test_campaign_report_rejects_misleading_inputs(path: tuple[str, ...], value: object, message: str) -> None:
    payload = _fixture()
    target: dict[str, Any] = payload
    for segment in path[:-1]:
        target = target[segment]
    target[path[-1]] = value

    with pytest.raises(ValueError, match=message):
        build_campaign_activation_report(**payload)


def _fixture() -> dict[str, Any]:
    return deepcopy(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
