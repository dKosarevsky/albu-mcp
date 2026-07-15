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
    assert add_historical_status_banner(rendered) == rendered


@pytest.mark.parametrize("path", HISTORICAL_DOCS)
def test_historical_document_has_banner(path: str) -> None:
    content = Path(path).read_text(encoding="utf-8")

    assert content.splitlines()[2].startswith("> **Historical status snapshot.**")
