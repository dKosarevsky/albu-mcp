# Lifecycle Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate published release health, optional host evidence, and the active adoption experiment in one concise status model without rewriting historical evidence.

**Architecture:** Add a pure lifecycle analysis module fed by committed release metadata, existing host blockers, and a small adoption-experiment JSON record. Public launch and growth exporters consume that model, while historical RC documents remain reproducible at their current paths and move behind an archive index.

**Tech Stack:** Python 3.10+, Pydantic, pytest with parametrization, existing deterministic Markdown exporters, Ruff, ty.

---

### Task 1: Pure Lifecycle Status Model

**Files:**
- Create: `src/albumentationsx_mcp/lifecycle.py`
- Create: `tests/test_lifecycle.py`

- [ ] **Step 1: Write failing separation and validation tests**

```python
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
```

- [ ] **Step 2: Run tests and confirm the missing module failure**

Run: `uv run pytest -q tests/test_lifecycle.py`

Expected: collection fails with `ModuleNotFoundError: No module named 'albumentationsx_mcp.lifecycle'`.

- [ ] **Step 3: Implement the pure lifecycle builder and renderer**

```python
"""Independent release, host-evidence, and adoption lifecycle status."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

_EXPERIMENT_STATUSES = {"planned", "measuring", "complete", "stopped"}
_READY_RELEASE_STATUSES = {"published", "listed", "merged", "ready"}


def build_lifecycle_status(
    *,
    version: str,
    release_channels: Sequence[Mapping[str, str]],
    host_blockers: Sequence[Mapping[str, str]],
    experiment: Mapping[str, Any],
) -> dict[str, Any]:
    """Build independent status dimensions from committed public metadata."""
    if not version.strip():
        raise ValueError("version must not be empty")
    channels = [dict(channel) for channel in release_channels]
    if not channels:
        raise ValueError("release_channels must not be empty")
    if len({channel["id"] for channel in channels}) != len(channels):
        raise ValueError("release channel ids must be unique")

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
    blocker_lines = "\n".join(
        f"- `{blocker['code']}`: {blocker['summary']}" for blocker in host["blockers"]
    ) or "- None"
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
        raise ValueError("measurement_due must not precede baseline_date")
    for field in ("campaign_id", "success_signal"):
        if not str(normalized.get(field, "")).strip():
            raise ValueError(f"{field} must not be empty")
    normalized["baseline_date"] = baseline.isoformat()
    normalized["measurement_due"] = measurement_due.isoformat()
    normalized.setdefault("post_url", None)
    return normalized
```

- [ ] **Step 4: Run lifecycle tests**

Run: `uv run pytest -q tests/test_lifecycle.py`

Expected: all tests pass.

- [ ] **Step 5: Commit the lifecycle model**

```bash
git add src/albumentationsx_mcp/lifecycle.py tests/test_lifecycle.py
git commit -m "feat: add independent lifecycle status"
```

### Task 2: Active Status Export And Public Consumers

**Files:**
- Create: `docs/ADOPTION_EXPERIMENT.json`
- Create: `scripts/export_lifecycle_status.py`
- Create: `docs/STATUS.md`
- Modify: `scripts/export_launch_kit.py`
- Modify: `scripts/export_network_growth_tracker.py`
- Modify: `tests/test_launch_kit.py`
- Modify: `tests/test_network_growth_tracker.py`
- Modify: `tests/test_lifecycle.py`

- [ ] **Step 1: Add failing exporter and consumer tests**

Add tests that assert:

```python
assert lifecycle["release_health"]["status"] == "published"
assert lifecycle["release_health"]["version"] == "1.19.0"
assert lifecycle["host_evidence"]["status"] == "partial"
assert lifecycle["adoption_experiment"]["campaign_id"] == "classification-robustness"
assert "Ready for v1" not in markdown
assert "Release health: `published`" in markdown
assert "Adoption experiment: `measuring`" in markdown
```

The committed-current test must compare `docs/STATUS.md` with
`render_lifecycle_status_markdown(build_committed_lifecycle_status())`.

- [ ] **Step 2: Run focused tests and confirm failures**

Run: `uv run pytest -q tests/test_lifecycle.py tests/test_launch_kit.py tests/test_network_growth_tracker.py`

Expected: failures for missing exporter/source and legacy `Ready for v1` rendering.

- [ ] **Step 3: Add the committed experiment record**

```json
{
  "baseline_date": "2026-07-14",
  "campaign_id": "classification-robustness",
  "measurement_due": "2026-07-21",
  "post_url": null,
  "status": "measuring",
  "success_signal": "One voluntary render -> reject -> adjust -> accept report."
}
```

- [ ] **Step 4: Implement `build_committed_lifecycle_status`**

`scripts/export_lifecycle_status.py` reads `docs/ADOPTION_EXPERIMENT.json`, reuses
`build_adoption_packet()` for version and URLs, and reuses `build_v1_launch_report()` only for host blockers. It passes
three release channels (`pypi`, `github_release`, `official_registry`) to `build_lifecycle_status` and exposes the
standard `--output` CLI used by other deterministic exporters.

- [ ] **Step 5: Replace legacy launch and growth booleans**

In both exporters, remove `ready_for_v1`. Store the lifecycle object under `lifecycle`. Render these exact lines:

```python
f"- Release health: `{kit['lifecycle']['release_health']['status']}`"
f"- Host evidence: `{kit['lifecycle']['host_evidence']['status']}`"
f"- Adoption experiment: `{kit['lifecycle']['adoption_experiment']['status']}`"
"- Details: `docs/STATUS.md`"
```

Keep host proof links, but replace `docs/V1_LAUNCH_REPORT.md` with `docs/STATUS.md` in active public asset lists.

- [ ] **Step 6: Generate committed status documents**

Run:

```bash
uv run python scripts/export_lifecycle_status.py --output docs/STATUS.md
uv run python scripts/export_launch_kit.py --output docs/LAUNCH_KIT.md
uv run python scripts/export_network_growth_tracker.py --output docs/NETWORK_GROWTH_TRACKER.md
```

Expected: all three files regenerate without `Ready for v1`.

- [ ] **Step 7: Run focused tests and commit**

Run: `uv run pytest -q tests/test_lifecycle.py tests/test_launch_kit.py tests/test_network_growth_tracker.py`

```bash
git add docs/ADOPTION_EXPERIMENT.json docs/STATUS.md docs/LAUNCH_KIT.md docs/NETWORK_GROWTH_TRACKER.md \
  scripts/export_lifecycle_status.py scripts/export_launch_kit.py scripts/export_network_growth_tracker.py \
  tests/test_lifecycle.py tests/test_launch_kit.py tests/test_network_growth_tracker.py
git commit -m "feat: separate active lifecycle status"
```

### Task 3: Historical RC Archive Navigation

**Files:**
- Create: `docs/ARCHIVE.md`
- Modify: `docs/INDEX.md`
- Modify: `tests/test_project_scaffolding.py`

- [ ] **Step 1: Add a failing navigation test**

```python
def test_active_docs_separate_historical_release_snapshots() -> None:
    index = Path("docs/INDEX.md").read_text(encoding="utf-8")
    archive = Path("docs/ARCHIVE.md").read_text(encoding="utf-8")

    assert "[STATUS.md](STATUS.md)" in index
    assert "[ARCHIVE.md](ARCHIVE.md)" in index
    assert "V1_RC_RELEASE_PACKET.md" not in index
    assert "RC_DRY_RUN.md" not in index
    assert "V1_RC_RELEASE_PACKET.md" in archive
    assert "RC_DRY_RUN.md" in archive
    assert "Historical status snapshots" in archive
```

- [ ] **Step 2: Run the test and confirm the missing archive failure**

Run: `uv run pytest -q tests/test_project_scaffolding.py -k historical_release_snapshots`

Expected: failure because `docs/ARCHIVE.md` does not exist.

- [ ] **Step 3: Add the archive index and simplify active navigation**

`docs/ARCHIVE.md` must explain that records remain immutable evidence snapshots, link the V1 readiness/decision reports,
all `V1_RC_*` documents, all `RC_*` documents, and state that current status is in `docs/STATUS.md`.

In `docs/INDEX.md`, add `STATUS.md` to the first operator section and replace direct V1/RC lists with one
`Historical Release Snapshots` section linking only `ARCHIVE.md`.

- [ ] **Step 4: Run the navigation test and commit**

Run: `uv run pytest -q tests/test_project_scaffolding.py -k historical_release_snapshots`

```bash
git add docs/ARCHIVE.md docs/INDEX.md tests/test_project_scaffolding.py
git commit -m "docs: separate historical release snapshots"
```

### Task 4: Historical Snapshot Banners

**Files:**
- Create: `scripts/historical_status.py`
- Modify: `scripts/export_v1_launch_report.py`
- Modify: `scripts/export_v1_decision_report.py`
- Modify: `scripts/export_v1_stabilization_plan.py`
- Modify: `scripts/export_v1_rc_readiness_report.py`
- Modify: `scripts/export_v1_rc_release_packet.py`
- Modify: `scripts/export_v1_rc_cutover_checklist.py`
- Modify: `scripts/export_v1_rc_automation_pack.py`
- Modify: `scripts/export_v1_rc_rehearsal_plan.py`
- Modify: `scripts/check_v1_rc_cutover_gate.py`
- Modify: `scripts/export_rc_cutover_recovery_plan.py`
- Modify: `scripts/export_rc_dry_run.py`
- Modify: `scripts/export_rc_evidence_reopen_flow.py`
- Modify: `scripts/export_rc_gate_reopen_packet.py`
- Modify: `scripts/export_rc_release_decision_report.py`
- Modify: `docs/V1_READINESS.md`
- Modify: `docs/V1_LAUNCH_REPORT.md`
- Modify: `docs/V1_DECISION_REPORT.md`
- Modify: `docs/V1_STABILIZATION_PLAN.md`
- Modify: `docs/V1_RC_READINESS.md`
- Modify: `docs/V1_RC_RELEASE_PACKET.md`
- Modify: `docs/V1_RC_CUTOVER_CHECKLIST.md`
- Modify: `docs/V1_RC_AUTOMATION_PACK.md`
- Modify: `docs/V1_RC_REHEARSAL_PLAN.md`
- Modify: `docs/V1_RC_CUTOVER_GATE.md`
- Modify: `docs/RC_CUTOVER_RECOVERY_PLAN.md`
- Modify: `docs/RC_DRY_RUN.md`
- Modify: `docs/RC_EVIDENCE_REOPEN_FLOW.md`
- Modify: `docs/RC_GATE_REOPEN_PACKET.md`
- Modify: `docs/RC_RELEASE_DECISION_REPORT.md`
- Create: `tests/test_historical_status.py`

- [ ] **Step 1: Add failing helper and parametrized document tests**

```python
from pathlib import Path

import pytest

from scripts.historical_status import add_historical_status_banner

HISTORICAL_DOCS = [
    "docs/V1_READINESS.md",
    "docs/V1_LAUNCH_REPORT.md",
    "docs/V1_DECISION_REPORT.md",
    "docs/V1_STABILIZATION_PLAN.md",
    "docs/V1_RC_READINESS.md",
    "docs/V1_RC_RELEASE_PACKET.md",
    "docs/V1_RC_CUTOVER_CHECKLIST.md",
    "docs/V1_RC_AUTOMATION_PACK.md",
    "docs/V1_RC_REHEARSAL_PLAN.md",
    "docs/V1_RC_CUTOVER_GATE.md",
    "docs/RC_CUTOVER_RECOVERY_PLAN.md",
    "docs/RC_DRY_RUN.md",
    "docs/RC_EVIDENCE_REOPEN_FLOW.md",
    "docs/RC_GATE_REOPEN_PACKET.md",
    "docs/RC_RELEASE_DECISION_REPORT.md",
]


def test_banner_is_inserted_after_title() -> None:
    rendered = add_historical_status_banner("# Report\n\nBody\n")
    assert rendered.startswith("# Report\n\n> **Historical status snapshot.**")
    assert rendered.endswith("Body\n")


@pytest.mark.parametrize("path", HISTORICAL_DOCS)
def test_historical_document_has_banner(path: str) -> None:
    content = Path(path).read_text(encoding="utf-8")
    assert content.splitlines()[2].startswith("> **Historical status snapshot.**")
```

- [ ] **Step 2: Implement the idempotent banner helper**

```python
HISTORICAL_STATUS_BANNER = (
    "> **Historical status snapshot.** This document preserves a pre-release decision and does not describe the "
    "current published release. See [STATUS.md](STATUS.md)."
)


def add_historical_status_banner(markdown: str) -> str:
    """Insert the historical-state warning after the first Markdown heading."""
    if HISTORICAL_STATUS_BANNER in markdown:
        return markdown
    title, separator, remainder = markdown.partition("\n")
    if not separator or not title.startswith("# "):
        raise ValueError("historical Markdown must start with an H1")
    return f"{title}\n\n{HISTORICAL_STATUS_BANNER}\n\n{remainder.lstrip()}"
```

- [ ] **Step 3: Wrap every deterministic historical renderer**

Import `add_historical_status_banner` and wrap the final Markdown return in these exporters:
`export_v1_launch_report.py`, `export_v1_decision_report.py`, `export_v1_stabilization_plan.py`,
`export_v1_rc_readiness_report.py`, `export_v1_rc_release_packet.py`, `export_v1_rc_cutover_checklist.py`,
`export_v1_rc_automation_pack.py`, `export_v1_rc_rehearsal_plan.py`, `check_v1_rc_cutover_gate.py`,
`export_rc_cutover_recovery_plan.py`, `export_rc_dry_run.py`, `export_rc_evidence_reopen_flow.py`,
`export_rc_gate_reopen_packet.py`, and `export_rc_release_decision_report.py`. Keep report payloads and historical
decisions unchanged. Add the same banner manually to `docs/V1_READINESS.md`, which has no deterministic exporter.

- [ ] **Step 4: Regenerate historical documents and run release-readiness freshness checks**

Run:

```bash
uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md
uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md
uv run python scripts/export_v1_stabilization_plan.py --output docs/V1_STABILIZATION_PLAN.md
uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md
uv run python scripts/export_v1_rc_release_packet.py --output docs/V1_RC_RELEASE_PACKET.md
uv run python scripts/export_v1_rc_cutover_checklist.py --output docs/V1_RC_CUTOVER_CHECKLIST.md
uv run python scripts/export_v1_rc_automation_pack.py --output docs/V1_RC_AUTOMATION_PACK.md
uv run python scripts/export_v1_rc_rehearsal_plan.py --output docs/V1_RC_REHEARSAL_PLAN.md
uv run python scripts/check_v1_rc_cutover_gate.py --output docs/V1_RC_CUTOVER_GATE.md
uv run python scripts/export_rc_cutover_recovery_plan.py --output docs/RC_CUTOVER_RECOVERY_PLAN.md
uv run python scripts/export_rc_dry_run.py --output docs/RC_DRY_RUN.md
uv run python scripts/export_rc_evidence_reopen_flow.py --output docs/RC_EVIDENCE_REOPEN_FLOW.md
uv run python scripts/export_rc_gate_reopen_packet.py --output docs/RC_GATE_REOPEN_PACKET.md
uv run python scripts/export_rc_release_decision_report.py --output docs/RC_RELEASE_DECISION_REPORT.md
uv run python scripts/check_release_readiness.py --tag v1.19.0
```

Expected: generated-document checks pass with no decision-state changes.

- [ ] **Step 5: Run parametrized tests and commit**

Run: `uv run pytest -q tests/test_historical_status.py tests/test_project_scaffolding.py`

```bash
git add scripts/historical_status.py scripts/export_v1_launch_report.py scripts/export_v1_decision_report.py \
  scripts/export_v1_stabilization_plan.py scripts/export_v1_rc_readiness_report.py \
  scripts/export_v1_rc_release_packet.py scripts/export_v1_rc_cutover_checklist.py \
  scripts/export_v1_rc_automation_pack.py scripts/export_v1_rc_rehearsal_plan.py \
  scripts/check_v1_rc_cutover_gate.py scripts/export_rc_cutover_recovery_plan.py scripts/export_rc_dry_run.py \
  scripts/export_rc_evidence_reopen_flow.py scripts/export_rc_gate_reopen_packet.py \
  scripts/export_rc_release_decision_report.py docs/V1_READINESS.md docs/V1_LAUNCH_REPORT.md \
  docs/V1_DECISION_REPORT.md docs/V1_STABILIZATION_PLAN.md docs/V1_RC_READINESS.md \
  docs/V1_RC_RELEASE_PACKET.md docs/V1_RC_CUTOVER_CHECKLIST.md docs/V1_RC_AUTOMATION_PACK.md \
  docs/V1_RC_REHEARSAL_PLAN.md docs/V1_RC_CUTOVER_GATE.md docs/RC_CUTOVER_RECOVERY_PLAN.md \
  docs/RC_DRY_RUN.md docs/RC_EVIDENCE_REOPEN_FLOW.md docs/RC_GATE_REOPEN_PACKET.md \
  docs/RC_RELEASE_DECISION_REPORT.md tests/test_historical_status.py
git commit -m "docs: mark historical lifecycle snapshots"
```

### Task 5: Lifecycle Slice Verification

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/plans/2026-07-14-lifecycle-truth.md`

- [ ] **Step 1: Add an Unreleased changelog entry**

Document the independent lifecycle dimensions and archive navigation without claiming a v1.20 release.

- [ ] **Step 2: Run focused and full verification**

Run:

```bash
uv run pytest -q tests/test_lifecycle.py tests/test_launch_kit.py tests/test_network_growth_tracker.py \
  tests/test_historical_status.py tests/test_project_scaffolding.py
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/check_contract_snapshots.py
uv run python scripts/check_release_readiness.py --tag v1.19.0
```

Expected: all commands pass; MCP contract snapshots remain unchanged.

- [ ] **Step 3: Mark completed plan checkboxes and commit verification metadata**

```bash
git add CHANGELOG.md docs/superpowers/plans/2026-07-14-lifecycle-truth.md
git commit -m "docs: complete lifecycle truth slice"
```
