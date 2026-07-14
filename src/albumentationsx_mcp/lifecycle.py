"""Independent release, host-evidence, and adoption lifecycle status."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

_EXPERIMENT_STATUSES = {"planned", "measuring", "complete", "stopped"}
_READY_RELEASE_STATUSES = {"published", "listed", "merged", "ready"}
_EMPTY_VERSION_ERROR = "version must not be empty"
_EMPTY_RELEASE_CHANNELS_ERROR = "release_channels must not be empty"
_DUPLICATE_RELEASE_CHANNELS_ERROR = "release channel ids must be unique"
_INVALID_EXPERIMENT_DATES_ERROR = "measurement_due must not precede baseline_date"


def build_lifecycle_status(
    *,
    version: str,
    release_channels: Sequence[Mapping[str, str]],
    host_blockers: Sequence[Mapping[str, str]],
    experiment: Mapping[str, Any],
) -> dict[str, Any]:
    """Build independent status dimensions from committed public metadata."""
    if not version.strip():
        raise ValueError(_EMPTY_VERSION_ERROR)
    channels = [dict(channel) for channel in release_channels]
    if not channels:
        raise ValueError(_EMPTY_RELEASE_CHANNELS_ERROR)
    if len({channel["id"] for channel in channels}) != len(channels):
        raise ValueError(_DUPLICATE_RELEASE_CHANNELS_ERROR)

    normalized_experiment = _validate_experiment(experiment)
    blockers = [dict(blocker) for blocker in host_blockers]
    release_ready = all(channel["status"] in _READY_RELEASE_STATUSES for channel in channels)
    return {
        "schema_version": 1,
        "release_health": {
            "status": "published" if release_ready else "attention_required",
            "version": version,
            "channels": channels,
        },
        "host_evidence": {
            "status": "complete" if not blockers else "partial",
            "unresolved_count": len(blockers),
            "blockers": blockers,
        },
        "adoption_experiment": normalized_experiment,
    }


def render_lifecycle_status_markdown(report: Mapping[str, Any]) -> str:
    """Render lifecycle dimensions without turning host gaps into release blockers."""
    release = report["release_health"]
    host = report["host_evidence"]
    experiment = report["adoption_experiment"]
    channel_lines = "\n".join(
        f"| {channel['id']} | `{channel['status']}` | {channel['url']} |" for channel in release["channels"]
    )
    blocker_lines = (
        "\n".join(f"- `{blocker['code']}`: {blocker['summary']}" for blocker in host["blockers"]) or "- None"
    )
    return (
        "# Project Lifecycle Status\n\n"
        "Release publication, host evidence, and adoption measurement are independent dimensions.\n\n"
        "## Release Health\n\n"
        f"Status: `{release['status']}`\n\nVersion: `{release['version']}`\n\n"
        "| Channel | Status | URL |\n| --- | --- | --- |\n"
        f"{channel_lines}\n\n"
        "## Host Evidence\n\n"
        f"Status: `{host['status']}`\n\nUnresolved observations: `{host['unresolved_count']}`\n\n"
        f"{blocker_lines}\n\n"
        "## Adoption Experiment\n\n"
        f"Campaign: `{experiment['campaign_id']}`\n\nStatus: `{experiment['status']}`\n\n"
        f"Baseline: `{experiment['baseline_date']}`\n\nMeasurement due: `{experiment['measurement_due']}`\n\n"
        f"Post URL: `{experiment['post_url'] or 'not_recorded'}`\n\n"
        f"Success signal: {experiment['success_signal']}\n"
    )


def _validate_experiment(experiment: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(experiment)
    status = normalized.get("status")
    if status not in _EXPERIMENT_STATUSES:
        raise ValueError(f"unsupported adoption experiment status: {status}")
    baseline = date.fromisoformat(str(normalized["baseline_date"]))
    measurement_due = date.fromisoformat(str(normalized["measurement_due"]))
    if measurement_due < baseline:
        raise ValueError(_INVALID_EXPERIMENT_DATES_ERROR)
    for field in ("campaign_id", "success_signal"):
        if not str(normalized.get(field, "")).strip():
            raise ValueError(f"{field} must not be empty")
    normalized["baseline_date"] = baseline.isoformat()
    normalized["measurement_due"] = measurement_due.isoformat()
    normalized.setdefault("post_url", None)
    return normalized
