"""Run fast release-readiness guards as one composable check."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_contract_snapshots import check_contract_snapshots
from scripts.check_first_10_minutes import check_first_10_minutes
from scripts.check_host_acceptance_report import check_host_acceptance_report
from scripts.check_host_proof_sprint import check_host_proof_sprint
from scripts.check_release_version import validate_release_versions
from scripts.export_beta_campaign_pack import build_beta_campaign_pack, render_beta_campaign_pack_markdown
from scripts.export_beta_feedback_intake import build_beta_feedback_intake, render_beta_feedback_intake_markdown
from scripts.export_beta_feedback_status import build_beta_feedback_status, render_beta_feedback_status_markdown
from scripts.export_beta_validation_sprint import build_beta_validation_sprint, render_beta_validation_sprint_markdown
from scripts.export_dataset_quality_depth_plan import (
    build_dataset_quality_depth_plan,
    render_dataset_quality_depth_plan_markdown,
)
from scripts.export_p0_blocker_triage import build_p0_blocker_triage, render_p0_blocker_triage_markdown
from scripts.export_p0_evidence_recorder import build_p0_evidence_recorder, render_p0_evidence_recorder_markdown
from scripts.export_p0_evidence_status import build_p0_evidence_status, render_p0_evidence_status_markdown
from scripts.export_p0_host_evidence_ledger import (
    build_p0_host_evidence_ledger,
    render_p0_host_evidence_ledger_markdown,
)
from scripts.export_p0_host_execution_sprint import (
    build_p0_host_execution_sprint,
    render_p0_host_execution_sprint_markdown,
)
from scripts.export_p0_host_runbook import build_p0_host_runbook, render_p0_host_runbook_markdown
from scripts.export_product_depth_backlog import build_product_depth_backlog, render_product_depth_backlog_markdown
from scripts.export_review_agent_v3_plan import build_review_agent_v3_plan, render_review_agent_v3_plan_markdown
from scripts.export_v1_decision_report import build_v1_decision_report, render_v1_decision_report_markdown
from scripts.export_v1_evidence_operator_packet import (
    build_v1_evidence_operator_packet,
    render_v1_evidence_operator_packet_markdown,
)
from scripts.export_v1_rc_automation_pack import build_v1_rc_automation_pack, render_v1_rc_automation_pack_markdown
from scripts.export_v1_rc_cutover_checklist import (
    build_v1_rc_cutover_checklist,
    render_v1_rc_cutover_checklist_markdown,
)
from scripts.export_v1_rc_readiness_report import (
    build_v1_rc_readiness_report,
    render_v1_rc_readiness_report_markdown,
)
from scripts.export_v1_rc_release_packet import build_v1_rc_release_packet, render_v1_rc_release_packet_markdown
from scripts.validate_host_manual_runs import validate_host_manual_runs

_DEFAULT_MANUAL_RUNS_PATH = Path("docs/HOST_MANUAL_RUNS.json")
_DEFAULT_HOST_REPORT_PATH = Path("docs/HOST_ACCEPTANCE_EVIDENCE.md")
_DEFAULT_V1_DECISION_REPORT_PATH = Path("docs/V1_DECISION_REPORT.md")
_DEFAULT_V1_EVIDENCE_OPERATOR_PACKET_PATH = Path("docs/V1_EVIDENCE_OPERATOR_PACKET.md")
_DEFAULT_V1_RC_READINESS_REPORT_PATH = Path("docs/V1_RC_READINESS.md")
_DEFAULT_P0_HOST_RUNBOOK_PATH = Path("docs/P0_HOST_RUNBOOK.md")
_DEFAULT_P0_EVIDENCE_RECORDER_PATH = Path("docs/P0_EVIDENCE_RECORDER.md")
_DEFAULT_P0_HOST_EXECUTION_SPRINT_PATH = Path("docs/P0_HOST_EXECUTION_SPRINT.md")
_DEFAULT_P0_HOST_EVIDENCE_LEDGER_PATH = Path("docs/P0_HOST_EVIDENCE_LEDGER.md")
_DEFAULT_P0_EVIDENCE_STATUS_PATH = Path("docs/P0_EVIDENCE_STATUS.md")
_DEFAULT_P0_BLOCKER_TRIAGE_PATH = Path("docs/P0_BLOCKER_TRIAGE.md")
_DEFAULT_BETA_CAMPAIGN_PACK_PATH = Path("docs/BETA_CAMPAIGN_PACK.md")
_DEFAULT_BETA_FEEDBACK_INTAKE_PATH = Path("docs/BETA_FEEDBACK_INTAKE.md")
_DEFAULT_BETA_FEEDBACK_STATUS_PATH = Path("docs/BETA_FEEDBACK_STATUS.md")
_DEFAULT_BETA_VALIDATION_SPRINT_PATH = Path("docs/BETA_VALIDATION_SPRINT.md")
_DEFAULT_V1_RC_RELEASE_PACKET_PATH = Path("docs/V1_RC_RELEASE_PACKET.md")
_DEFAULT_V1_RC_CUTOVER_CHECKLIST_PATH = Path("docs/V1_RC_CUTOVER_CHECKLIST.md")
_DEFAULT_V1_RC_AUTOMATION_PACK_PATH = Path("docs/V1_RC_AUTOMATION_PACK.md")
_DEFAULT_PRODUCT_DEPTH_BACKLOG_PATH = Path("docs/PRODUCT_DEPTH_BACKLOG.md")
_DEFAULT_REVIEW_AGENT_V3_PLAN_PATH = Path("docs/REVIEW_AGENT_V3_PLAN.md")
_DEFAULT_DATASET_QUALITY_DEPTH_PLAN_PATH = Path("docs/DATASET_QUALITY_DEPTH_PLAN.md")
_DEFAULT_MCP_SNAPSHOT_PATH = Path("tests/fixtures/snapshots/mcp_contract.json")
_DEFAULT_OUTPUT_SNAPSHOT_PATH = Path("tests/fixtures/snapshots/output_contracts.json")
_DEFAULT_PYPROJECT_PATH = Path("pyproject.toml")
_DEFAULT_SERVER_JSON_PATH = Path("server.json")


@dataclass(frozen=True)
class ReleaseReadinessConfig:
    """Inputs for fast release-readiness guards."""

    tag: str | None = None
    manual_runs_path: Path = _DEFAULT_MANUAL_RUNS_PATH
    host_report_root: Path = Path()
    host_report_path: Path = _DEFAULT_HOST_REPORT_PATH
    v1_decision_report_path: Path = _DEFAULT_V1_DECISION_REPORT_PATH
    v1_evidence_operator_packet_path: Path = _DEFAULT_V1_EVIDENCE_OPERATOR_PACKET_PATH
    v1_rc_readiness_report_path: Path = _DEFAULT_V1_RC_READINESS_REPORT_PATH
    p0_host_runbook_path: Path = _DEFAULT_P0_HOST_RUNBOOK_PATH
    p0_evidence_recorder_path: Path = _DEFAULT_P0_EVIDENCE_RECORDER_PATH
    p0_host_execution_sprint_path: Path = _DEFAULT_P0_HOST_EXECUTION_SPRINT_PATH
    p0_host_evidence_ledger_path: Path = _DEFAULT_P0_HOST_EVIDENCE_LEDGER_PATH
    p0_evidence_status_path: Path = _DEFAULT_P0_EVIDENCE_STATUS_PATH
    p0_blocker_triage_path: Path = _DEFAULT_P0_BLOCKER_TRIAGE_PATH
    beta_campaign_pack_path: Path = _DEFAULT_BETA_CAMPAIGN_PACK_PATH
    beta_feedback_intake_path: Path = _DEFAULT_BETA_FEEDBACK_INTAKE_PATH
    beta_feedback_status_path: Path = _DEFAULT_BETA_FEEDBACK_STATUS_PATH
    beta_validation_sprint_path: Path = _DEFAULT_BETA_VALIDATION_SPRINT_PATH
    v1_rc_release_packet_path: Path = _DEFAULT_V1_RC_RELEASE_PACKET_PATH
    v1_rc_cutover_checklist_path: Path = _DEFAULT_V1_RC_CUTOVER_CHECKLIST_PATH
    v1_rc_automation_pack_path: Path = _DEFAULT_V1_RC_AUTOMATION_PACK_PATH
    product_depth_backlog_path: Path = _DEFAULT_PRODUCT_DEPTH_BACKLOG_PATH
    review_agent_v3_plan_path: Path = _DEFAULT_REVIEW_AGENT_V3_PLAN_PATH
    dataset_quality_depth_plan_path: Path = _DEFAULT_DATASET_QUALITY_DEPTH_PLAN_PATH
    mcp_snapshot_path: Path = _DEFAULT_MCP_SNAPSHOT_PATH
    output_snapshot_path: Path = _DEFAULT_OUTPUT_SNAPSHOT_PATH
    contract_output_work_dir: Path | None = None
    pyproject_path: Path = _DEFAULT_PYPROJECT_PATH
    server_json_path: Path = _DEFAULT_SERVER_JSON_PATH


@dataclass(frozen=True)
class ReleaseReadinessCheck:
    """One release-readiness guard result."""

    name: str
    ok: bool
    message: str
    diff: str = ""


@dataclass(frozen=True)
class ReleaseReadinessReport:
    """Aggregate release-readiness result."""

    checks: list[ReleaseReadinessCheck]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)


def check_release_readiness(config: ReleaseReadinessConfig | None = None) -> ReleaseReadinessReport:
    """Run fast local release guards and return structured results."""
    config = config or ReleaseReadinessConfig()
    checks = [
        _check_manual_host_records(config.manual_runs_path),
        _check_host_acceptance_evidence(root=config.host_report_root, report_path=config.host_report_path),
        _check_first_10_minutes_entrypoints(),
        _check_host_proof_sprint_entrypoints(),
        _check_v1_decision_report(config.v1_decision_report_path),
        _check_generated_doc(
            name="v1_evidence_operator_packet",
            path=config.v1_evidence_operator_packet_path,
            expected=render_v1_evidence_operator_packet_markdown(build_v1_evidence_operator_packet()),
            exporter="scripts/export_v1_evidence_operator_packet.py",
        ),
        _check_v1_rc_readiness_report(config.v1_rc_readiness_report_path),
        _check_generated_doc(
            name="p0_host_runbook",
            path=config.p0_host_runbook_path,
            expected=render_p0_host_runbook_markdown(build_p0_host_runbook()),
            exporter="scripts/export_p0_host_runbook.py",
        ),
        _check_generated_doc(
            name="p0_evidence_recorder",
            path=config.p0_evidence_recorder_path,
            expected=render_p0_evidence_recorder_markdown(build_p0_evidence_recorder()),
            exporter="scripts/export_p0_evidence_recorder.py",
        ),
        _check_generated_doc(
            name="p0_host_execution_sprint",
            path=config.p0_host_execution_sprint_path,
            expected=render_p0_host_execution_sprint_markdown(build_p0_host_execution_sprint()),
            exporter="scripts/export_p0_host_execution_sprint.py",
        ),
        _check_generated_doc(
            name="p0_host_evidence_ledger",
            path=config.p0_host_evidence_ledger_path,
            expected=render_p0_host_evidence_ledger_markdown(build_p0_host_evidence_ledger()),
            exporter="scripts/export_p0_host_evidence_ledger.py",
        ),
        _check_generated_doc(
            name="p0_evidence_status",
            path=config.p0_evidence_status_path,
            expected=render_p0_evidence_status_markdown(build_p0_evidence_status()),
            exporter="scripts/export_p0_evidence_status.py",
        ),
        _check_generated_doc(
            name="p0_blocker_triage",
            path=config.p0_blocker_triage_path,
            expected=render_p0_blocker_triage_markdown(build_p0_blocker_triage()),
            exporter="scripts/export_p0_blocker_triage.py",
        ),
        _check_generated_doc(
            name="beta_campaign_pack",
            path=config.beta_campaign_pack_path,
            expected=render_beta_campaign_pack_markdown(build_beta_campaign_pack()),
            exporter="scripts/export_beta_campaign_pack.py",
        ),
        _check_generated_doc(
            name="beta_feedback_intake",
            path=config.beta_feedback_intake_path,
            expected=render_beta_feedback_intake_markdown(build_beta_feedback_intake()),
            exporter="scripts/export_beta_feedback_intake.py",
        ),
        _check_generated_doc(
            name="beta_feedback_status",
            path=config.beta_feedback_status_path,
            expected=render_beta_feedback_status_markdown(build_beta_feedback_status()),
            exporter="scripts/export_beta_feedback_status.py",
        ),
        _check_generated_doc(
            name="beta_validation_sprint",
            path=config.beta_validation_sprint_path,
            expected=render_beta_validation_sprint_markdown(build_beta_validation_sprint()),
            exporter="scripts/export_beta_validation_sprint.py",
        ),
        _check_generated_doc(
            name="v1_rc_release_packet",
            path=config.v1_rc_release_packet_path,
            expected=render_v1_rc_release_packet_markdown(build_v1_rc_release_packet()),
            exporter="scripts/export_v1_rc_release_packet.py",
        ),
        _check_generated_doc(
            name="v1_rc_cutover_checklist",
            path=config.v1_rc_cutover_checklist_path,
            expected=render_v1_rc_cutover_checklist_markdown(build_v1_rc_cutover_checklist()),
            exporter="scripts/export_v1_rc_cutover_checklist.py",
        ),
        _check_generated_doc(
            name="v1_rc_automation_pack",
            path=config.v1_rc_automation_pack_path,
            expected=render_v1_rc_automation_pack_markdown(build_v1_rc_automation_pack()),
            exporter="scripts/export_v1_rc_automation_pack.py",
        ),
        _check_generated_doc(
            name="product_depth_backlog",
            path=config.product_depth_backlog_path,
            expected=render_product_depth_backlog_markdown(build_product_depth_backlog()),
            exporter="scripts/export_product_depth_backlog.py",
        ),
        _check_generated_doc(
            name="review_agent_v3_plan",
            path=config.review_agent_v3_plan_path,
            expected=render_review_agent_v3_plan_markdown(build_review_agent_v3_plan()),
            exporter="scripts/export_review_agent_v3_plan.py",
        ),
        _check_generated_doc(
            name="dataset_quality_depth_plan",
            path=config.dataset_quality_depth_plan_path,
            expected=render_dataset_quality_depth_plan_markdown(build_dataset_quality_depth_plan()),
            exporter="scripts/export_dataset_quality_depth_plan.py",
        ),
        *_check_contract_snapshot_freshness(
            mcp_snapshot_path=config.mcp_snapshot_path,
            output_snapshot_path=config.output_snapshot_path,
            output_work_dir=config.contract_output_work_dir,
        ),
    ]
    if config.tag is not None:
        checks.append(
            _check_release_version(
                config.tag,
                pyproject_path=config.pyproject_path,
                server_json_path=config.server_json_path,
            )
        )
    return ReleaseReadinessReport(checks=checks)


def main() -> None:
    """CLI entrypoint for CI and local release readiness checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=None, help="Optional release tag, for example v1.10.0.")
    parser.add_argument("--manual-runs", type=Path, default=_DEFAULT_MANUAL_RUNS_PATH)
    parser.add_argument("--host-report-root", type=Path, default=Path())
    parser.add_argument("--host-report", type=Path, default=None)
    parser.add_argument("--v1-decision-report", type=Path, default=_DEFAULT_V1_DECISION_REPORT_PATH)
    parser.add_argument("--v1-evidence-operator-packet", type=Path, default=_DEFAULT_V1_EVIDENCE_OPERATOR_PACKET_PATH)
    parser.add_argument("--v1-rc-readiness-report", type=Path, default=_DEFAULT_V1_RC_READINESS_REPORT_PATH)
    parser.add_argument("--p0-host-runbook", type=Path, default=_DEFAULT_P0_HOST_RUNBOOK_PATH)
    parser.add_argument("--p0-evidence-recorder", type=Path, default=_DEFAULT_P0_EVIDENCE_RECORDER_PATH)
    parser.add_argument("--p0-host-execution-sprint", type=Path, default=_DEFAULT_P0_HOST_EXECUTION_SPRINT_PATH)
    parser.add_argument("--p0-host-evidence-ledger", type=Path, default=_DEFAULT_P0_HOST_EVIDENCE_LEDGER_PATH)
    parser.add_argument("--p0-evidence-status", type=Path, default=_DEFAULT_P0_EVIDENCE_STATUS_PATH)
    parser.add_argument("--p0-blocker-triage", type=Path, default=_DEFAULT_P0_BLOCKER_TRIAGE_PATH)
    parser.add_argument("--beta-campaign-pack", type=Path, default=_DEFAULT_BETA_CAMPAIGN_PACK_PATH)
    parser.add_argument("--beta-feedback-intake", type=Path, default=_DEFAULT_BETA_FEEDBACK_INTAKE_PATH)
    parser.add_argument("--beta-feedback-status", type=Path, default=_DEFAULT_BETA_FEEDBACK_STATUS_PATH)
    parser.add_argument("--beta-validation-sprint", type=Path, default=_DEFAULT_BETA_VALIDATION_SPRINT_PATH)
    parser.add_argument("--v1-rc-release-packet", type=Path, default=_DEFAULT_V1_RC_RELEASE_PACKET_PATH)
    parser.add_argument("--v1-rc-cutover-checklist", type=Path, default=_DEFAULT_V1_RC_CUTOVER_CHECKLIST_PATH)
    parser.add_argument("--v1-rc-automation-pack", type=Path, default=_DEFAULT_V1_RC_AUTOMATION_PACK_PATH)
    parser.add_argument("--product-depth-backlog", type=Path, default=_DEFAULT_PRODUCT_DEPTH_BACKLOG_PATH)
    parser.add_argument("--review-agent-v3-plan", type=Path, default=_DEFAULT_REVIEW_AGENT_V3_PLAN_PATH)
    parser.add_argument("--dataset-quality-depth-plan", type=Path, default=_DEFAULT_DATASET_QUALITY_DEPTH_PLAN_PATH)
    parser.add_argument("--mcp-snapshot", type=Path, default=_DEFAULT_MCP_SNAPSHOT_PATH)
    parser.add_argument("--output-snapshot", type=Path, default=_DEFAULT_OUTPUT_SNAPSHOT_PATH)
    parser.add_argument("--contract-output-work-dir", type=Path, default=None)
    parser.add_argument("--pyproject", type=Path, default=_DEFAULT_PYPROJECT_PATH)
    parser.add_argument("--server-json", type=Path, default=_DEFAULT_SERVER_JSON_PATH)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    host_report_path = (
        args.host_report if args.host_report is not None else args.host_report_root / _DEFAULT_HOST_REPORT_PATH
    )
    report = check_release_readiness(
        ReleaseReadinessConfig(
            tag=args.tag,
            manual_runs_path=args.manual_runs,
            host_report_root=args.host_report_root,
            host_report_path=host_report_path,
            v1_decision_report_path=args.v1_decision_report,
            v1_evidence_operator_packet_path=args.v1_evidence_operator_packet,
            v1_rc_readiness_report_path=args.v1_rc_readiness_report,
            p0_host_runbook_path=args.p0_host_runbook,
            p0_evidence_recorder_path=args.p0_evidence_recorder,
            p0_host_execution_sprint_path=args.p0_host_execution_sprint,
            p0_host_evidence_ledger_path=args.p0_host_evidence_ledger,
            p0_evidence_status_path=args.p0_evidence_status,
            p0_blocker_triage_path=args.p0_blocker_triage,
            beta_campaign_pack_path=args.beta_campaign_pack,
            beta_feedback_intake_path=args.beta_feedback_intake,
            beta_feedback_status_path=args.beta_feedback_status,
            beta_validation_sprint_path=args.beta_validation_sprint,
            v1_rc_release_packet_path=args.v1_rc_release_packet,
            v1_rc_cutover_checklist_path=args.v1_rc_cutover_checklist,
            v1_rc_automation_pack_path=args.v1_rc_automation_pack,
            product_depth_backlog_path=args.product_depth_backlog,
            review_agent_v3_plan_path=args.review_agent_v3_plan,
            dataset_quality_depth_plan_path=args.dataset_quality_depth_plan,
            mcp_snapshot_path=args.mcp_snapshot,
            output_snapshot_path=args.output_snapshot,
            contract_output_work_dir=args.contract_output_work_dir,
            pyproject_path=args.pyproject,
            server_json_path=args.server_json,
        )
    )
    _write_github_step_summary(report)
    if args.format == "json":
        sys.stdout.write(json.dumps(_report_payload(report), indent=2))
        sys.stdout.write("\n")
    if not report.ok:
        if args.format == "text":
            _write_text_failures(report)
        raise SystemExit(1)

    if args.format == "text":
        checked = ", ".join(check.name for check in report.checks)
        sys.stdout.write(f"release readiness checks passed: {checked}\n")


def _check_manual_host_records(path: Path) -> ReleaseReadinessCheck:
    try:
        manual_runs = validate_host_manual_runs(path)
    except (OSError, ValueError) as exc:
        return ReleaseReadinessCheck(name="manual_host_records", ok=False, message=str(exc))
    return ReleaseReadinessCheck(
        name="manual_host_records",
        ok=True,
        message=f"manual host run records are valid ({len(manual_runs.manual_host_ui)} recorded)",
    )


def _check_host_acceptance_evidence(*, root: Path, report_path: Path) -> ReleaseReadinessCheck:
    try:
        result = check_host_acceptance_report(root=root, report_path=report_path)
    except (OSError, ValueError) as exc:
        return ReleaseReadinessCheck(name="host_acceptance_evidence", ok=False, message=str(exc))
    return ReleaseReadinessCheck(
        name="host_acceptance_evidence",
        ok=result.ok,
        message=result.message,
        diff=result.diff,
    )


def _check_first_10_minutes_entrypoints() -> ReleaseReadinessCheck:
    report = check_first_10_minutes()
    failed = [check for check in report.checks if not check.ok]
    if failed:
        return ReleaseReadinessCheck(
            name="first_10_minutes",
            ok=False,
            message="; ".join(f"{check.name}: {check.message}" for check in failed),
        )
    return ReleaseReadinessCheck(
        name="first_10_minutes",
        ok=True,
        message=f"first-10-minutes entrypoints are valid ({len(report.checks)} checks)",
    )


def _check_host_proof_sprint_entrypoints() -> ReleaseReadinessCheck:
    report = check_host_proof_sprint()
    failed = [check for check in report.checks if not check.ok]
    if failed:
        return ReleaseReadinessCheck(
            name="host_proof_sprint",
            ok=False,
            message="; ".join(f"{check.name}: {check.message}" for check in failed),
        )
    return ReleaseReadinessCheck(
        name="host_proof_sprint",
        ok=True,
        message=f"host proof sprint entrypoints are valid ({len(report.checks)} checks)",
    )


def _check_v1_decision_report(path: Path) -> ReleaseReadinessCheck:
    try:
        expected = render_v1_decision_report_markdown(build_v1_decision_report())
        current = path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        return ReleaseReadinessCheck(name="v1_decision_report", ok=False, message=str(exc))
    if current != expected:
        return ReleaseReadinessCheck(
            name="v1_decision_report",
            ok=False,
            message=f"{path} is stale; regenerate it with scripts/export_v1_decision_report.py",
        )
    return ReleaseReadinessCheck(
        name="v1_decision_report",
        ok=True,
        message=f"{path} is current",
    )


def _check_v1_rc_readiness_report(path: Path) -> ReleaseReadinessCheck:
    try:
        expected = render_v1_rc_readiness_report_markdown(build_v1_rc_readiness_report())
        current = path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        return ReleaseReadinessCheck(name="v1_rc_readiness_report", ok=False, message=str(exc))
    if current != expected:
        return ReleaseReadinessCheck(
            name="v1_rc_readiness_report",
            ok=False,
            message=f"{path} is stale; regenerate it with scripts/export_v1_rc_readiness_report.py",
        )
    return ReleaseReadinessCheck(
        name="v1_rc_readiness_report",
        ok=True,
        message=f"{path} is current",
    )


def _check_generated_doc(*, name: str, path: Path, expected: str, exporter: str) -> ReleaseReadinessCheck:
    try:
        current = path.read_text(encoding="utf-8")
    except OSError as exc:
        return ReleaseReadinessCheck(name=name, ok=False, message=str(exc))
    if current != expected:
        return ReleaseReadinessCheck(
            name=name,
            ok=False,
            message=f"{path} is stale; regenerate it with {exporter}",
        )
    return ReleaseReadinessCheck(name=name, ok=True, message=f"{path} is current")


def _check_contract_snapshot_freshness(
    *,
    mcp_snapshot_path: Path,
    output_snapshot_path: Path,
    output_work_dir: Path | None,
) -> list[ReleaseReadinessCheck]:
    try:
        report = check_contract_snapshots(
            mcp_snapshot_path=mcp_snapshot_path,
            output_snapshot_path=output_snapshot_path,
            output_work_dir=output_work_dir,
        )
    except (OSError, ValueError) as exc:
        return [
            ReleaseReadinessCheck(name="mcp_contract_snapshot", ok=False, message=str(exc)),
            ReleaseReadinessCheck(name="output_contract_snapshot", ok=False, message=str(exc)),
        ]

    names = {
        "mcp_contract": "mcp_contract_snapshot",
        "output_contracts": "output_contract_snapshot",
    }
    return [
        ReleaseReadinessCheck(
            name=names[check.name],
            ok=check.ok,
            message=check.message,
            diff=check.diff,
        )
        for check in report.checks
    ]


def _check_release_version(tag: str, *, pyproject_path: Path, server_json_path: Path) -> ReleaseReadinessCheck:
    try:
        report = validate_release_versions(tag, pyproject_path=pyproject_path, server_json_path=server_json_path)
    except (OSError, StopIteration, ValueError) as exc:
        return ReleaseReadinessCheck(name="release_version", ok=False, message=str(exc))
    return ReleaseReadinessCheck(
        name="release_version",
        ok=True,
        message=f"release version {report.version} is consistent",
    )


def _report_payload(report: ReleaseReadinessReport) -> dict[str, object]:
    return {"ok": report.ok, "checks": [asdict(check) for check in report.checks]}


def _write_text_failures(report: ReleaseReadinessReport) -> None:
    for check in report.checks:
        if check.ok:
            continue
        sys.stderr.write(f"[{check.name}] {check.message}\n")
        if check.diff:
            sys.stderr.write(check.diff)


def _write_github_step_summary(report: ReleaseReadinessReport) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    Path(summary_path).parent.mkdir(parents=True, exist_ok=True)
    Path(summary_path).write_text(_github_step_summary(report), encoding="utf-8")


def _github_step_summary(report: ReleaseReadinessReport) -> str:
    lines = [
        "## Release Readiness",
        "",
        "| Check | Status | Message |",
        "| --- | --- | --- |",
    ]
    for check in report.checks:
        status = "passed" if check.ok else "failed"
        lines.append(f"| {check.name} | {status} | {_escape_markdown_cell(check.message)} |")
    lines.append("")
    return "\n".join(lines)


def _escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


if __name__ == "__main__":
    main()
