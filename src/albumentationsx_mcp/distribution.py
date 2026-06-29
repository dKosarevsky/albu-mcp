"""Report-only public distribution readiness checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from albumentationsx_mcp.rc_reopen import build_rc_reopen_report

_CHANNELS = ("pypi", "github_release", "mcp_registry", "upstream_docs")


def build_distribution_readiness_report(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
) -> dict[str, Any]:
    """Build a report-only public distribution readiness decision."""
    rc_report = build_rc_reopen_report(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    publish_allowed = bool(rc_report["publish_allowed"])
    blocked_reasons = [] if publish_allowed else ["rc_reopen_not_allowed", *rc_report["blocked_reasons"]]
    channels = {
        channel: {
            "status": "ready" if publish_allowed else "blocked",
            "blocked_reasons": blocked_reasons,
        }
        for channel in _CHANNELS
    }
    return {
        "distribution_status": "ready_for_public_release" if publish_allowed else "blocked",
        "release_tag": release_tag,
        "publish_allowed": publish_allowed,
        "execution_policy": "report_only",
        "channels": channels,
        "rc_reopen": rc_report,
        "next_actions": _next_actions(publish_allowed=publish_allowed),
    }


def _next_actions(*, publish_allowed: bool) -> list[str]:
    if publish_allowed:
        return [
            "Review report-only publish commands before creating tags or releases.",
            "Publish release notes, PyPI package, MCP Registry metadata, and upstream docs in one coordinated pass.",
        ]
    return [
        "Do not publish public release artifacts until trust gates pass.",
        "Complete P0 real-host evidence and beta validation records first.",
    ]
