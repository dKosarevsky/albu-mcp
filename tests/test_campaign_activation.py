from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from albumentationsx_mcp.campaign_activation import (
    build_campaign_activation_report,
    render_campaign_activation_markdown,
)
from scripts import public_metrics_sources

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
        "publications": [],
        "attribution_ready": False,
    }
    assert report["activation"]["attributed_reports"] == 4
    assert report["activation"]["completed_loops"] == 3
    assert report["activation"]["distinct_submitters"] == 2
    assert report["activation"]["target_met"] is False
    assert "no publication URL and timestamp are recorded" in report["warnings"]
    assert report["privacy"] == {
        "runtime_telemetry": False,
        "reads_local_data": False,
        "contains_issue_level_data": False,
        "issue_data_usage": "aggregate voluntary public issue fields and public timestamps in memory only",
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


def test_campaign_report_preserves_only_public_publication_metadata() -> None:
    payload = _fixture()
    payload["config"]["publications"] = [
        {
            "channel": "github-release",
            "url": "https://github.com/dKosarevsky/albu-mcp/releases/tag/v1.21.1",
            "published_at": "2026-08-13T10:30:00+00:00",
        }
    ]

    report = build_campaign_activation_report(**payload)

    assert report["campaign"]["attribution_ready"] is True
    assert report["campaign"]["publications"] == payload["config"]["publications"]
    assert "no publication URL and timestamp are recorded" not in report["warnings"]


def test_campaign_report_defers_future_publications_until_their_observed_date() -> None:
    payload = _fixture()
    payload["config"]["publications"] = [
        {
            "channel": "github-release",
            "url": "https://github.com/dKosarevsky/albu-mcp/releases/tag/v1.21.1",
            "published_at": "2026-08-21T10:30:00+00:00",
        }
    ]

    report = build_campaign_activation_report(**payload)

    assert report["campaign"]["attribution_ready"] is False
    assert report["campaign"]["publications"] == []
    assert "no recorded publication had occurred by report as_of" in report["warnings"]


def test_campaign_report_counts_feedback_only_inside_the_observed_campaign_window() -> None:
    payload = _fixture()
    completed = payload["workflow_feedback_issues"][0]
    for issue_id, created_at in (
        (106, "2026-08-12T23:59:59Z"),
        (107, "2026-08-21T00:00:00Z"),
        (108, "2026-08-27T00:00:00Z"),
        (109, "not-a-timestamp"),
    ):
        issue = deepcopy(completed)
        issue["id"] = issue_id
        issue["user"] = {"login": f"excluded-{issue_id}"}
        issue["created_at"] = created_at
        payload["workflow_feedback_issues"].append(issue)

    report = build_campaign_activation_report(**payload)

    assert report["activation"]["attributed_reports"] == 4
    assert report["activation"]["completed_loops"] == 3
    assert report["activation"]["distinct_submitters"] == 2
    assert "3 workflow feedback issue(s) fell outside the observed campaign window" in report["warnings"]
    assert "1 workflow feedback issue(s) had no valid created_at and were ignored" in report["warnings"]


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
        (
            ("config", "publications"),
            [
                {
                    "channel": "discord",
                    "url": "http://example.invalid/post",
                    "published_at": "2026-08-13T10:30:00+00:00",
                }
            ],
            "publication 0 url",
        ),
        (
            ("config", "publications"),
            [
                {
                    "channel": "github-release",
                    "url": "https://github.com/dKosarevsky/albu-mcp/releases/tag/v1.21.1",
                    "published_at": "2026-08-27T00:00:00+00:00",
                }
            ],
            "publication 0 timestamp must fall inside the campaign window",
        ),
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


@pytest.mark.parametrize("output_format", ["markdown", "json"])
def test_activation_cli_supports_reproducible_offline_input(tmp_path: Path, output_format: str) -> None:
    output_path = tmp_path / f"activation.{'md' if output_format == 'markdown' else 'json'}"

    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "scripts/export_campaign_activation_report.py",
            "--input",
            str(FIXTURE_PATH),
            "--format",
            output_format,
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    if output_format == "markdown":
        assert content.startswith("# Campaign Activation Report\n")
        assert "Recommendation: `continue`" in content
    else:
        report = json.loads(content)
        assert report["campaign"]["id"] == "classification-robustness"
        assert report["privacy"]["contains_issue_level_data"] is False
    for private_value in PRIVATE_VALUES:
        assert private_value not in content


def test_feedback_issue_source_fetches_every_page_without_returning_pull_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = [
        [{"id": index, "body": "body"} for index in range(99)]
        + [{"id": 99, "body": "body", "pull_request": {"url": "https://example.invalid/pr/99"}}],
        [{"id": 100, "body": "body"}],
    ]
    requested_urls: list[str] = []

    def fake_fetch_json(url: str, *, headers: dict[str, str]) -> object:
        requested_urls.append(url)
        assert headers["Authorization"] == "Bearer token"
        return pages[len(requested_urls) - 1]

    monkeypatch.setattr(public_metrics_sources, "_fetch_json", fake_fetch_json)

    issues = public_metrics_sources.fetch_workflow_feedback_issues(
        repository="dKosarevsky/albu-mcp",
        token="token",  # noqa: S106
    )

    assert len(issues) == 100
    assert all("pull_request" not in issue for issue in issues)
    assert requested_urls == [
        "https://api.github.com/repos/dKosarevsky/albu-mcp/issues?state=all&labels=workflow-feedback&per_page=100&page=1",
        "https://api.github.com/repos/dKosarevsky/albu-mcp/issues?state=all&labels=workflow-feedback&per_page=100&page=2",
    ]


def test_committed_campaign_config_preserves_the_real_prepublication_baseline() -> None:
    config = json.loads(Path("docs/campaigns/classification-robustness-2026-08.json").read_text(encoding="utf-8"))

    assert config["baseline_captured_at"] == "2026-08-13T05:10:44.265052+00:00"
    assert config["baseline_as_of"] == "2026-08-12"
    assert config["baseline"] == {
        "github_unique_visitors": 3,
        "mcpb_downloads_total": 22,
        "completed_loops": 0,
        "distinct_submitters": 0,
        "pypi_last_7_days": 121,
        "pypi_previous_7_days": 298,
        "pypi_previous_7_days_complete": False,
        "release_excluded_median_daily": None,
    }
    assert config["targets"] == {
        "github_unique_visitors": 20,
        "mcpb_downloads_increment": 5,
        "completed_loops": 3,
        "distinct_submitters": 3,
    }
    assert config["publications"] == []


def test_growth_guide_documents_the_activation_report_boundary() -> None:
    guide = Path("docs/GROWTH.md").read_text(encoding="utf-8")

    assert "scripts/export_campaign_activation_report.py" in guide
    assert "classification-robustness-2026-08.json" in guide
    assert "issue bodies" in guide
    assert "distinct submitters" in guide


def _fixture() -> dict[str, Any]:
    return deepcopy(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
