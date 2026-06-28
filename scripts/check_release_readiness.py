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
from scripts.check_host_setup_probe import build_host_setup_probe, render_host_setup_probe_markdown
from scripts.check_p0_host_run_preflight import check_p0_host_run_preflight
from scripts.check_release_version import validate_release_versions
from scripts.check_v1_rc_cutover_gate import build_v1_rc_cutover_gate, render_v1_rc_cutover_gate_markdown
from scripts.export_beta_campaign_execution import (
    build_beta_campaign_execution,
    render_beta_campaign_execution_markdown,
)
from scripts.export_beta_campaign_pack import build_beta_campaign_pack, render_beta_campaign_pack_markdown
from scripts.export_beta_feedback_intake import build_beta_feedback_intake, render_beta_feedback_intake_markdown
from scripts.export_beta_feedback_status import build_beta_feedback_status, render_beta_feedback_status_markdown
from scripts.export_beta_to_backlog_triage import (
    build_beta_to_backlog_triage,
    render_beta_to_backlog_triage_markdown,
)
from scripts.export_beta_validation_intake import (
    build_beta_validation_intake,
    render_beta_validation_intake_markdown,
)
from scripts.export_beta_validation_loop import build_beta_validation_loop, render_beta_validation_loop_markdown
from scripts.export_beta_validation_recording_pack import (
    build_beta_validation_recording_pack,
    render_beta_validation_recording_pack_markdown,
)
from scripts.export_beta_validation_sprint import build_beta_validation_sprint, render_beta_validation_sprint_markdown
from scripts.export_beta_validation_status import (
    build_beta_validation_status,
    render_beta_validation_status_markdown,
)
from scripts.export_claude_code_setup_path import (
    build_claude_code_setup_path,
    render_claude_code_setup_path_markdown,
)
from scripts.export_codex_cancellation_triage import (
    build_codex_cancellation_triage,
    render_codex_cancellation_triage_markdown,
)
from scripts.export_dataset_quality_depth_plan import (
    build_dataset_quality_depth_plan,
    render_dataset_quality_depth_plan_markdown,
)
from scripts.export_distribution_readiness_pack import (
    build_distribution_readiness_pack,
    render_distribution_readiness_pack_markdown,
)
from scripts.export_distribution_rollout_packet import (
    build_distribution_rollout_packet,
    render_distribution_rollout_packet_markdown,
)
from scripts.export_evidence_first_cycle_report import (
    build_evidence_first_cycle_report,
    render_evidence_first_cycle_report_markdown,
)
from scripts.export_host_evidence_runner import build_host_evidence_runner, render_host_evidence_runner_markdown
from scripts.export_host_onboarding_depth_plan import (
    build_host_onboarding_depth_plan,
    render_host_onboarding_depth_plan_markdown,
)
from scripts.export_p0_blocker_triage import build_p0_blocker_triage, render_p0_blocker_triage_markdown
from scripts.export_p0_evidence_recorder import build_p0_evidence_recorder, render_p0_evidence_recorder_markdown
from scripts.export_p0_evidence_regeneration_pack import (
    build_p0_evidence_regeneration_pack,
    render_p0_evidence_regeneration_pack_markdown,
)
from scripts.export_p0_evidence_status import build_p0_evidence_status, render_p0_evidence_status_markdown
from scripts.export_p0_host_evidence_ledger import (
    build_p0_host_evidence_ledger,
    render_p0_host_evidence_ledger_markdown,
)
from scripts.export_p0_host_evidence_recovery import (
    build_p0_host_evidence_recovery,
    render_p0_host_evidence_recovery_markdown,
)
from scripts.export_p0_host_execution_sprint import (
    build_p0_host_execution_sprint,
    render_p0_host_execution_sprint_markdown,
)
from scripts.export_p0_host_run_session import build_p0_host_run_session, render_p0_host_run_session_markdown
from scripts.export_p0_host_runbook import build_p0_host_runbook, render_p0_host_runbook_markdown
from scripts.export_p0_host_unblock_pack import build_p0_host_unblock_pack, render_p0_host_unblock_pack_markdown
from scripts.export_policy_assistant_plan import build_policy_assistant_plan, render_policy_assistant_plan_markdown
from scripts.export_product_depth_backlog import build_product_depth_backlog, render_product_depth_backlog_markdown
from scripts.export_product_depth_gate import build_product_depth_gate, render_product_depth_gate_markdown
from scripts.export_product_depth_selection import (
    build_product_depth_selection,
    render_product_depth_selection_markdown,
)
from scripts.export_product_iteration_governor import (
    build_product_iteration_governor,
    render_product_iteration_governor_markdown,
)
from scripts.export_rc_cutover_recovery_plan import (
    build_rc_cutover_recovery_plan,
    render_rc_cutover_recovery_plan_markdown,
)
from scripts.export_rc_dry_run import build_rc_dry_run, render_rc_dry_run_markdown
from scripts.export_rc_evidence_reopen_flow import (
    build_rc_evidence_reopen_flow,
    render_rc_evidence_reopen_flow_markdown,
)
from scripts.export_rc_gate_reopen_packet import build_rc_gate_reopen_packet, render_rc_gate_reopen_packet_markdown
from scripts.export_rc_host_evidence_ops import build_rc_host_evidence_ops, render_rc_host_evidence_ops_markdown
from scripts.export_real_host_evidence_command_center import (
    build_real_host_evidence_command_center,
    render_real_host_evidence_command_center_markdown,
)
from scripts.export_review_agent_v3_plan import build_review_agent_v3_plan, render_review_agent_v3_plan_markdown
from scripts.export_v1_decision_report import build_v1_decision_report, render_v1_decision_report_markdown
from scripts.export_v1_evidence_operator_packet import (
    build_v1_evidence_operator_packet,
    render_v1_evidence_operator_packet_markdown,
)
from scripts.export_v1_growth_cutover_report import (
    build_v1_growth_cutover_report,
    render_v1_growth_cutover_report_markdown,
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
from scripts.export_v1_rc_rehearsal_plan import build_v1_rc_rehearsal_plan, render_v1_rc_rehearsal_plan_markdown
from scripts.export_v1_rc_release_packet import build_v1_rc_release_packet, render_v1_rc_release_packet_markdown
from scripts.export_v1_stabilization_plan import (
    build_v1_stabilization_plan,
    render_v1_stabilization_plan_markdown,
)
from scripts.export_v1_trust_gates import build_v1_trust_gates, render_v1_trust_gates_markdown
from scripts.validate_host_manual_runs import validate_host_manual_runs
from scripts.verify_host_evidence_import import (
    build_host_evidence_import_guide,
    render_host_evidence_import_guide_markdown,
)

_DEFAULT_MANUAL_RUNS_PATH = Path("docs/HOST_MANUAL_RUNS.json")
_DEFAULT_HOST_REPORT_PATH = Path("docs/HOST_ACCEPTANCE_EVIDENCE.md")
_DEFAULT_V1_DECISION_REPORT_PATH = Path("docs/V1_DECISION_REPORT.md")
_DEFAULT_V1_EVIDENCE_OPERATOR_PACKET_PATH = Path("docs/V1_EVIDENCE_OPERATOR_PACKET.md")
_DEFAULT_V1_GROWTH_CUTOVER_REPORT_PATH = Path("docs/V1_GROWTH_CUTOVER_REPORT.md")
_DEFAULT_V1_STABILIZATION_PLAN_PATH = Path("docs/V1_STABILIZATION_PLAN.md")
_DEFAULT_V1_TRUST_GATES_PATH = Path("docs/V1_TRUST_GATES.md")
_DEFAULT_V1_RC_READINESS_REPORT_PATH = Path("docs/V1_RC_READINESS.md")
_DEFAULT_P0_HOST_RUNBOOK_PATH = Path("docs/P0_HOST_RUNBOOK.md")
_DEFAULT_P0_HOST_RUN_SESSION_PATH = Path("docs/P0_HOST_RUN_SESSION.md")
_DEFAULT_P0_EVIDENCE_RECORDER_PATH = Path("docs/P0_EVIDENCE_RECORDER.md")
_DEFAULT_P0_EVIDENCE_IMPORT_GUIDE_PATH = Path("docs/P0_EVIDENCE_IMPORT_GUIDE.md")
_DEFAULT_P0_EVIDENCE_REGENERATION_PACK_PATH = Path("docs/P0_EVIDENCE_REGENERATION_PACK.md")
_DEFAULT_P0_HOST_EXECUTION_SPRINT_PATH = Path("docs/P0_HOST_EXECUTION_SPRINT.md")
_DEFAULT_P0_HOST_EVIDENCE_LEDGER_PATH = Path("docs/P0_HOST_EVIDENCE_LEDGER.md")
_DEFAULT_P0_EVIDENCE_STATUS_PATH = Path("docs/P0_EVIDENCE_STATUS.md")
_DEFAULT_P0_BLOCKER_TRIAGE_PATH = Path("docs/P0_BLOCKER_TRIAGE.md")
_DEFAULT_P0_HOST_UNBLOCK_PACK_PATH = Path("docs/P0_HOST_UNBLOCK_PACK.md")
_DEFAULT_P0_HOST_EVIDENCE_RECOVERY_PATH = Path("docs/P0_HOST_EVIDENCE_RECOVERY.md")
_DEFAULT_HOST_EVIDENCE_RUNNER_PATH = Path("docs/HOST_EVIDENCE_RUNNER.md")
_DEFAULT_CODEX_CANCELLATION_TRIAGE_PATH = Path("docs/CODEX_CANCELLATION_TRIAGE.md")
_DEFAULT_CLAUDE_CODE_SETUP_PATH = Path("docs/CLAUDE_CODE_SETUP_PATH.md")
_DEFAULT_HOST_SETUP_PROBE_PATH = Path("docs/HOST_SETUP_PROBE.md")
_DEFAULT_REAL_HOST_EVIDENCE_COMMAND_CENTER_PATH = Path("docs/REAL_HOST_EVIDENCE_COMMAND_CENTER.md")
_DEFAULT_BETA_CAMPAIGN_PACK_PATH = Path("docs/BETA_CAMPAIGN_PACK.md")
_DEFAULT_BETA_CAMPAIGN_EXECUTION_PATH = Path("docs/BETA_CAMPAIGN_EXECUTION.md")
_DEFAULT_BETA_FEEDBACK_INTAKE_PATH = Path("docs/BETA_FEEDBACK_INTAKE.md")
_DEFAULT_BETA_FEEDBACK_STATUS_PATH = Path("docs/BETA_FEEDBACK_STATUS.md")
_DEFAULT_BETA_TO_BACKLOG_TRIAGE_PATH = Path("docs/BETA_TO_BACKLOG_TRIAGE.md")
_DEFAULT_BETA_VALIDATION_INTAKE_PATH = Path("docs/BETA_VALIDATION_INTAKE.md")
_DEFAULT_BETA_VALIDATION_LOOP_PATH = Path("docs/BETA_VALIDATION_LOOP.md")
_DEFAULT_BETA_VALIDATION_RECORDING_PACK_PATH = Path("docs/BETA_VALIDATION_RECORDING_PACK.md")
_DEFAULT_BETA_VALIDATION_SPRINT_PATH = Path("docs/BETA_VALIDATION_SPRINT.md")
_DEFAULT_BETA_VALIDATION_STATUS_PATH = Path("docs/BETA_VALIDATION_STATUS.md")
_DEFAULT_V1_RC_RELEASE_PACKET_PATH = Path("docs/V1_RC_RELEASE_PACKET.md")
_DEFAULT_V1_RC_CUTOVER_CHECKLIST_PATH = Path("docs/V1_RC_CUTOVER_CHECKLIST.md")
_DEFAULT_V1_RC_AUTOMATION_PACK_PATH = Path("docs/V1_RC_AUTOMATION_PACK.md")
_DEFAULT_V1_RC_REHEARSAL_PLAN_PATH = Path("docs/V1_RC_REHEARSAL_PLAN.md")
_DEFAULT_V1_RC_CUTOVER_GATE_PATH = Path("docs/V1_RC_CUTOVER_GATE.md")
_DEFAULT_RC_CUTOVER_RECOVERY_PLAN_PATH = Path("docs/RC_CUTOVER_RECOVERY_PLAN.md")
_DEFAULT_RC_DRY_RUN_PATH = Path("docs/RC_DRY_RUN.md")
_DEFAULT_RC_EVIDENCE_REOPEN_FLOW_PATH = Path("docs/RC_EVIDENCE_REOPEN_FLOW.md")
_DEFAULT_RC_GATE_REOPEN_PACKET_PATH = Path("docs/RC_GATE_REOPEN_PACKET.md")
_DEFAULT_RC_HOST_EVIDENCE_OPS_PATH = Path("docs/RC_HOST_EVIDENCE_OPS.md")
_DEFAULT_PRODUCT_DEPTH_BACKLOG_PATH = Path("docs/PRODUCT_DEPTH_BACKLOG.md")
_DEFAULT_PRODUCT_DEPTH_GATE_PATH = Path("docs/PRODUCT_DEPTH_GATE.md")
_DEFAULT_PRODUCT_DEPTH_SELECTION_PATH = Path("docs/PRODUCT_DEPTH_SELECTION.md")
_DEFAULT_POLICY_ASSISTANT_PLAN_PATH = Path("docs/POLICY_ASSISTANT_PLAN.md")
_DEFAULT_PRODUCT_ITERATION_GOVERNOR_PATH = Path("docs/PRODUCT_ITERATION_GOVERNOR.md")
_DEFAULT_HOST_ONBOARDING_DEPTH_PLAN_PATH = Path("docs/HOST_ONBOARDING_DEPTH_PLAN.md")
_DEFAULT_REVIEW_AGENT_V3_PLAN_PATH = Path("docs/REVIEW_AGENT_V3_PLAN.md")
_DEFAULT_DATASET_QUALITY_DEPTH_PLAN_PATH = Path("docs/DATASET_QUALITY_DEPTH_PLAN.md")
_DEFAULT_DISTRIBUTION_READINESS_PACK_PATH = Path("docs/DISTRIBUTION_READINESS_PACK.md")
_DEFAULT_DISTRIBUTION_ROLLOUT_PACKET_PATH = Path("docs/DISTRIBUTION_ROLLOUT_PACKET.md")
_DEFAULT_EVIDENCE_FIRST_CYCLE_REPORT_PATH = Path("docs/EVIDENCE_FIRST_CYCLE_REPORT.md")
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
    v1_growth_cutover_report_path: Path = _DEFAULT_V1_GROWTH_CUTOVER_REPORT_PATH
    v1_stabilization_plan_path: Path = _DEFAULT_V1_STABILIZATION_PLAN_PATH
    v1_trust_gates_path: Path = _DEFAULT_V1_TRUST_GATES_PATH
    v1_rc_readiness_report_path: Path = _DEFAULT_V1_RC_READINESS_REPORT_PATH
    p0_host_runbook_path: Path = _DEFAULT_P0_HOST_RUNBOOK_PATH
    p0_host_run_session_path: Path = _DEFAULT_P0_HOST_RUN_SESSION_PATH
    p0_evidence_recorder_path: Path = _DEFAULT_P0_EVIDENCE_RECORDER_PATH
    p0_evidence_import_guide_path: Path = _DEFAULT_P0_EVIDENCE_IMPORT_GUIDE_PATH
    p0_evidence_regeneration_pack_path: Path = _DEFAULT_P0_EVIDENCE_REGENERATION_PACK_PATH
    p0_host_execution_sprint_path: Path = _DEFAULT_P0_HOST_EXECUTION_SPRINT_PATH
    p0_host_evidence_ledger_path: Path = _DEFAULT_P0_HOST_EVIDENCE_LEDGER_PATH
    p0_evidence_status_path: Path = _DEFAULT_P0_EVIDENCE_STATUS_PATH
    p0_blocker_triage_path: Path = _DEFAULT_P0_BLOCKER_TRIAGE_PATH
    p0_host_unblock_pack_path: Path = _DEFAULT_P0_HOST_UNBLOCK_PACK_PATH
    p0_host_evidence_recovery_path: Path = _DEFAULT_P0_HOST_EVIDENCE_RECOVERY_PATH
    host_evidence_runner_path: Path = _DEFAULT_HOST_EVIDENCE_RUNNER_PATH
    codex_cancellation_triage_path: Path = _DEFAULT_CODEX_CANCELLATION_TRIAGE_PATH
    claude_code_setup_path: Path = _DEFAULT_CLAUDE_CODE_SETUP_PATH
    host_setup_probe_path: Path = _DEFAULT_HOST_SETUP_PROBE_PATH
    real_host_evidence_command_center_path: Path = _DEFAULT_REAL_HOST_EVIDENCE_COMMAND_CENTER_PATH
    beta_campaign_pack_path: Path = _DEFAULT_BETA_CAMPAIGN_PACK_PATH
    beta_campaign_execution_path: Path = _DEFAULT_BETA_CAMPAIGN_EXECUTION_PATH
    beta_feedback_intake_path: Path = _DEFAULT_BETA_FEEDBACK_INTAKE_PATH
    beta_feedback_status_path: Path = _DEFAULT_BETA_FEEDBACK_STATUS_PATH
    beta_to_backlog_triage_path: Path = _DEFAULT_BETA_TO_BACKLOG_TRIAGE_PATH
    beta_validation_intake_path: Path = _DEFAULT_BETA_VALIDATION_INTAKE_PATH
    beta_validation_loop_path: Path = _DEFAULT_BETA_VALIDATION_LOOP_PATH
    beta_validation_recording_pack_path: Path = _DEFAULT_BETA_VALIDATION_RECORDING_PACK_PATH
    beta_validation_sprint_path: Path = _DEFAULT_BETA_VALIDATION_SPRINT_PATH
    beta_validation_status_path: Path = _DEFAULT_BETA_VALIDATION_STATUS_PATH
    v1_rc_release_packet_path: Path = _DEFAULT_V1_RC_RELEASE_PACKET_PATH
    v1_rc_cutover_checklist_path: Path = _DEFAULT_V1_RC_CUTOVER_CHECKLIST_PATH
    v1_rc_automation_pack_path: Path = _DEFAULT_V1_RC_AUTOMATION_PACK_PATH
    v1_rc_rehearsal_plan_path: Path = _DEFAULT_V1_RC_REHEARSAL_PLAN_PATH
    v1_rc_cutover_gate_path: Path = _DEFAULT_V1_RC_CUTOVER_GATE_PATH
    rc_cutover_recovery_plan_path: Path = _DEFAULT_RC_CUTOVER_RECOVERY_PLAN_PATH
    rc_dry_run_path: Path = _DEFAULT_RC_DRY_RUN_PATH
    rc_evidence_reopen_flow_path: Path = _DEFAULT_RC_EVIDENCE_REOPEN_FLOW_PATH
    rc_gate_reopen_packet_path: Path = _DEFAULT_RC_GATE_REOPEN_PACKET_PATH
    rc_host_evidence_ops_path: Path = _DEFAULT_RC_HOST_EVIDENCE_OPS_PATH
    product_depth_backlog_path: Path = _DEFAULT_PRODUCT_DEPTH_BACKLOG_PATH
    product_depth_gate_path: Path = _DEFAULT_PRODUCT_DEPTH_GATE_PATH
    product_depth_selection_path: Path = _DEFAULT_PRODUCT_DEPTH_SELECTION_PATH
    policy_assistant_plan_path: Path = _DEFAULT_POLICY_ASSISTANT_PLAN_PATH
    product_iteration_governor_path: Path = _DEFAULT_PRODUCT_ITERATION_GOVERNOR_PATH
    host_onboarding_depth_plan_path: Path = _DEFAULT_HOST_ONBOARDING_DEPTH_PLAN_PATH
    review_agent_v3_plan_path: Path = _DEFAULT_REVIEW_AGENT_V3_PLAN_PATH
    dataset_quality_depth_plan_path: Path = _DEFAULT_DATASET_QUALITY_DEPTH_PLAN_PATH
    distribution_readiness_pack_path: Path = _DEFAULT_DISTRIBUTION_READINESS_PACK_PATH
    distribution_rollout_packet_path: Path = _DEFAULT_DISTRIBUTION_ROLLOUT_PACKET_PATH
    evidence_first_cycle_report_path: Path = _DEFAULT_EVIDENCE_FIRST_CYCLE_REPORT_PATH
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
        _check_p0_host_run_preflight(),
        _check_v1_decision_report(config.v1_decision_report_path),
        _check_generated_doc(
            name="v1_evidence_operator_packet",
            path=config.v1_evidence_operator_packet_path,
            expected=render_v1_evidence_operator_packet_markdown(build_v1_evidence_operator_packet()),
            exporter="scripts/export_v1_evidence_operator_packet.py",
        ),
        _check_generated_doc(
            name="v1_growth_cutover_report",
            path=config.v1_growth_cutover_report_path,
            expected=render_v1_growth_cutover_report_markdown(build_v1_growth_cutover_report()),
            exporter="scripts/export_v1_growth_cutover_report.py",
        ),
        _check_generated_doc(
            name="v1_stabilization_plan",
            path=config.v1_stabilization_plan_path,
            expected=render_v1_stabilization_plan_markdown(build_v1_stabilization_plan()),
            exporter="scripts/export_v1_stabilization_plan.py --output docs/V1_STABILIZATION_PLAN.md",
        ),
        _check_generated_doc(
            name="v1_trust_gates",
            path=config.v1_trust_gates_path,
            expected=render_v1_trust_gates_markdown(build_v1_trust_gates()),
            exporter="scripts/export_v1_trust_gates.py --output docs/V1_TRUST_GATES.md",
        ),
        _check_v1_rc_readiness_report(config.v1_rc_readiness_report_path),
        _check_generated_doc(
            name="p0_host_runbook",
            path=config.p0_host_runbook_path,
            expected=render_p0_host_runbook_markdown(build_p0_host_runbook()),
            exporter="scripts/export_p0_host_runbook.py",
        ),
        _check_generated_doc(
            name="p0_host_run_session",
            path=config.p0_host_run_session_path,
            expected=render_p0_host_run_session_markdown(build_p0_host_run_session()),
            exporter="scripts/export_p0_host_run_session.py",
        ),
        _check_generated_doc(
            name="p0_evidence_recorder",
            path=config.p0_evidence_recorder_path,
            expected=render_p0_evidence_recorder_markdown(build_p0_evidence_recorder()),
            exporter="scripts/export_p0_evidence_recorder.py",
        ),
        _check_generated_doc(
            name="p0_evidence_import_guide",
            path=config.p0_evidence_import_guide_path,
            expected=render_host_evidence_import_guide_markdown(build_host_evidence_import_guide()),
            exporter="scripts/verify_host_evidence_import.py --output docs/P0_EVIDENCE_IMPORT_GUIDE.md",
        ),
        _check_generated_doc(
            name="p0_evidence_regeneration_pack",
            path=config.p0_evidence_regeneration_pack_path,
            expected=render_p0_evidence_regeneration_pack_markdown(build_p0_evidence_regeneration_pack()),
            exporter="scripts/export_p0_evidence_regeneration_pack.py --output docs/P0_EVIDENCE_REGENERATION_PACK.md",
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
            name="p0_host_unblock_pack",
            path=config.p0_host_unblock_pack_path,
            expected=render_p0_host_unblock_pack_markdown(build_p0_host_unblock_pack()),
            exporter="scripts/export_p0_host_unblock_pack.py --output docs/P0_HOST_UNBLOCK_PACK.md",
        ),
        _check_generated_doc(
            name="p0_host_evidence_recovery",
            path=config.p0_host_evidence_recovery_path,
            expected=render_p0_host_evidence_recovery_markdown(build_p0_host_evidence_recovery()),
            exporter="scripts/export_p0_host_evidence_recovery.py --output docs/P0_HOST_EVIDENCE_RECOVERY.md",
        ),
        _check_generated_doc(
            name="host_evidence_runner",
            path=config.host_evidence_runner_path,
            expected=render_host_evidence_runner_markdown(build_host_evidence_runner()),
            exporter="scripts/export_host_evidence_runner.py --output docs/HOST_EVIDENCE_RUNNER.md",
        ),
        _check_generated_doc(
            name="codex_cancellation_triage",
            path=config.codex_cancellation_triage_path,
            expected=render_codex_cancellation_triage_markdown(build_codex_cancellation_triage()),
            exporter="scripts/export_codex_cancellation_triage.py --output docs/CODEX_CANCELLATION_TRIAGE.md",
        ),
        _check_generated_doc(
            name="claude_code_setup_path",
            path=config.claude_code_setup_path,
            expected=render_claude_code_setup_path_markdown(build_claude_code_setup_path()),
            exporter="scripts/export_claude_code_setup_path.py --output docs/CLAUDE_CODE_SETUP_PATH.md",
        ),
        _check_generated_doc(
            name="host_setup_probe",
            path=config.host_setup_probe_path,
            expected=render_host_setup_probe_markdown(build_host_setup_probe()),
            exporter="scripts/check_host_setup_probe.py --output docs/HOST_SETUP_PROBE.md",
        ),
        _check_generated_doc(
            name="real_host_evidence_command_center",
            path=config.real_host_evidence_command_center_path,
            expected=render_real_host_evidence_command_center_markdown(build_real_host_evidence_command_center()),
            exporter=(
                "scripts/export_real_host_evidence_command_center.py --output docs/REAL_HOST_EVIDENCE_COMMAND_CENTER.md"
            ),
        ),
        _check_generated_doc(
            name="beta_campaign_pack",
            path=config.beta_campaign_pack_path,
            expected=render_beta_campaign_pack_markdown(build_beta_campaign_pack()),
            exporter="scripts/export_beta_campaign_pack.py",
        ),
        _check_generated_doc(
            name="beta_campaign_execution",
            path=config.beta_campaign_execution_path,
            expected=render_beta_campaign_execution_markdown(build_beta_campaign_execution()),
            exporter="scripts/export_beta_campaign_execution.py --output docs/BETA_CAMPAIGN_EXECUTION.md",
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
            name="beta_to_backlog_triage",
            path=config.beta_to_backlog_triage_path,
            expected=render_beta_to_backlog_triage_markdown(build_beta_to_backlog_triage()),
            exporter="scripts/export_beta_to_backlog_triage.py --output docs/BETA_TO_BACKLOG_TRIAGE.md",
        ),
        _check_generated_doc(
            name="beta_validation_intake",
            path=config.beta_validation_intake_path,
            expected=render_beta_validation_intake_markdown(build_beta_validation_intake()),
            exporter="scripts/export_beta_validation_intake.py --output docs/BETA_VALIDATION_INTAKE.md",
        ),
        _check_generated_doc(
            name="beta_validation_loop",
            path=config.beta_validation_loop_path,
            expected=render_beta_validation_loop_markdown(build_beta_validation_loop()),
            exporter="scripts/export_beta_validation_loop.py --output docs/BETA_VALIDATION_LOOP.md",
        ),
        _check_generated_doc(
            name="beta_validation_recording_pack",
            path=config.beta_validation_recording_pack_path,
            expected=render_beta_validation_recording_pack_markdown(build_beta_validation_recording_pack()),
            exporter=(
                "scripts/export_beta_validation_recording_pack.py --output docs/BETA_VALIDATION_RECORDING_PACK.md"
            ),
        ),
        _check_generated_doc(
            name="beta_validation_sprint",
            path=config.beta_validation_sprint_path,
            expected=render_beta_validation_sprint_markdown(build_beta_validation_sprint()),
            exporter="scripts/export_beta_validation_sprint.py",
        ),
        _check_generated_doc(
            name="beta_validation_status",
            path=config.beta_validation_status_path,
            expected=render_beta_validation_status_markdown(build_beta_validation_status()),
            exporter="scripts/export_beta_validation_status.py --output docs/BETA_VALIDATION_STATUS.md",
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
            name="v1_rc_rehearsal_plan",
            path=config.v1_rc_rehearsal_plan_path,
            expected=render_v1_rc_rehearsal_plan_markdown(build_v1_rc_rehearsal_plan()),
            exporter="scripts/export_v1_rc_rehearsal_plan.py --output docs/V1_RC_REHEARSAL_PLAN.md",
        ),
        _check_generated_doc(
            name="v1_rc_cutover_gate",
            path=config.v1_rc_cutover_gate_path,
            expected=render_v1_rc_cutover_gate_markdown(build_v1_rc_cutover_gate()),
            exporter="scripts/check_v1_rc_cutover_gate.py --output docs/V1_RC_CUTOVER_GATE.md",
        ),
        _check_generated_doc(
            name="rc_cutover_recovery_plan",
            path=config.rc_cutover_recovery_plan_path,
            expected=render_rc_cutover_recovery_plan_markdown(build_rc_cutover_recovery_plan()),
            exporter="scripts/export_rc_cutover_recovery_plan.py --output docs/RC_CUTOVER_RECOVERY_PLAN.md",
        ),
        _check_generated_doc(
            name="rc_dry_run",
            path=config.rc_dry_run_path,
            expected=render_rc_dry_run_markdown(build_rc_dry_run()),
            exporter="scripts/export_rc_dry_run.py --output docs/RC_DRY_RUN.md",
        ),
        _check_generated_doc(
            name="rc_evidence_reopen_flow",
            path=config.rc_evidence_reopen_flow_path,
            expected=render_rc_evidence_reopen_flow_markdown(build_rc_evidence_reopen_flow()),
            exporter="scripts/export_rc_evidence_reopen_flow.py --output docs/RC_EVIDENCE_REOPEN_FLOW.md",
        ),
        _check_generated_doc(
            name="rc_gate_reopen_packet",
            path=config.rc_gate_reopen_packet_path,
            expected=render_rc_gate_reopen_packet_markdown(build_rc_gate_reopen_packet()),
            exporter="scripts/export_rc_gate_reopen_packet.py --output docs/RC_GATE_REOPEN_PACKET.md",
        ),
        _check_generated_doc(
            name="rc_host_evidence_ops",
            path=config.rc_host_evidence_ops_path,
            expected=render_rc_host_evidence_ops_markdown(build_rc_host_evidence_ops()),
            exporter="scripts/export_rc_host_evidence_ops.py --output docs/RC_HOST_EVIDENCE_OPS.md",
        ),
        _check_generated_doc(
            name="product_depth_backlog",
            path=config.product_depth_backlog_path,
            expected=render_product_depth_backlog_markdown(build_product_depth_backlog()),
            exporter="scripts/export_product_depth_backlog.py",
        ),
        _check_generated_doc(
            name="product_depth_gate",
            path=config.product_depth_gate_path,
            expected=render_product_depth_gate_markdown(build_product_depth_gate()),
            exporter="scripts/export_product_depth_gate.py --output docs/PRODUCT_DEPTH_GATE.md",
        ),
        _check_generated_doc(
            name="product_depth_selection",
            path=config.product_depth_selection_path,
            expected=render_product_depth_selection_markdown(build_product_depth_selection()),
            exporter="scripts/export_product_depth_selection.py --output docs/PRODUCT_DEPTH_SELECTION.md",
        ),
        _check_generated_doc(
            name="policy_assistant_plan",
            path=config.policy_assistant_plan_path,
            expected=render_policy_assistant_plan_markdown(build_policy_assistant_plan()),
            exporter="scripts/export_policy_assistant_plan.py --output docs/POLICY_ASSISTANT_PLAN.md",
        ),
        _check_generated_doc(
            name="product_iteration_governor",
            path=config.product_iteration_governor_path,
            expected=render_product_iteration_governor_markdown(build_product_iteration_governor()),
            exporter="scripts/export_product_iteration_governor.py --output docs/PRODUCT_ITERATION_GOVERNOR.md",
        ),
        _check_generated_doc(
            name="host_onboarding_depth_plan",
            path=config.host_onboarding_depth_plan_path,
            expected=render_host_onboarding_depth_plan_markdown(build_host_onboarding_depth_plan()),
            exporter="scripts/export_host_onboarding_depth_plan.py --output docs/HOST_ONBOARDING_DEPTH_PLAN.md",
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
        _check_generated_doc(
            name="distribution_readiness_pack",
            path=config.distribution_readiness_pack_path,
            expected=render_distribution_readiness_pack_markdown(build_distribution_readiness_pack()),
            exporter="scripts/export_distribution_readiness_pack.py --output docs/DISTRIBUTION_READINESS_PACK.md",
        ),
        _check_generated_doc(
            name="distribution_rollout_packet",
            path=config.distribution_rollout_packet_path,
            expected=render_distribution_rollout_packet_markdown(build_distribution_rollout_packet()),
            exporter="scripts/export_distribution_rollout_packet.py --output docs/DISTRIBUTION_ROLLOUT_PACKET.md",
        ),
        _check_generated_doc(
            name="evidence_first_cycle_report",
            path=config.evidence_first_cycle_report_path,
            expected=render_evidence_first_cycle_report_markdown(build_evidence_first_cycle_report()),
            exporter="scripts/export_evidence_first_cycle_report.py --output docs/EVIDENCE_FIRST_CYCLE_REPORT.md",
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
    args = _build_arg_parser().parse_args()

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
            v1_growth_cutover_report_path=args.v1_growth_cutover_report,
            v1_stabilization_plan_path=args.v1_stabilization_plan,
            v1_rc_readiness_report_path=args.v1_rc_readiness_report,
            p0_host_runbook_path=args.p0_host_runbook,
            p0_host_run_session_path=args.p0_host_run_session,
            p0_evidence_recorder_path=args.p0_evidence_recorder,
            p0_evidence_import_guide_path=args.p0_evidence_import_guide,
            p0_evidence_regeneration_pack_path=args.p0_evidence_regeneration_pack,
            p0_host_execution_sprint_path=args.p0_host_execution_sprint,
            p0_host_evidence_ledger_path=args.p0_host_evidence_ledger,
            p0_evidence_status_path=args.p0_evidence_status,
            p0_blocker_triage_path=args.p0_blocker_triage,
            p0_host_unblock_pack_path=args.p0_host_unblock_pack,
            p0_host_evidence_recovery_path=args.p0_host_evidence_recovery,
            host_evidence_runner_path=args.host_evidence_runner,
            codex_cancellation_triage_path=args.codex_cancellation_triage,
            claude_code_setup_path=args.claude_code_setup_path,
            host_setup_probe_path=args.host_setup_probe,
            beta_campaign_pack_path=args.beta_campaign_pack,
            beta_campaign_execution_path=args.beta_campaign_execution,
            beta_feedback_intake_path=args.beta_feedback_intake,
            beta_feedback_status_path=args.beta_feedback_status,
            beta_to_backlog_triage_path=args.beta_to_backlog_triage,
            beta_validation_intake_path=args.beta_validation_intake,
            beta_validation_recording_pack_path=args.beta_validation_recording_pack,
            beta_validation_sprint_path=args.beta_validation_sprint,
            v1_rc_release_packet_path=args.v1_rc_release_packet,
            v1_rc_cutover_checklist_path=args.v1_rc_cutover_checklist,
            v1_rc_automation_pack_path=args.v1_rc_automation_pack,
            v1_rc_rehearsal_plan_path=args.v1_rc_rehearsal_plan,
            v1_rc_cutover_gate_path=args.v1_rc_cutover_gate,
            rc_cutover_recovery_plan_path=args.rc_cutover_recovery_plan,
            rc_dry_run_path=args.rc_dry_run,
            rc_gate_reopen_packet_path=args.rc_gate_reopen_packet,
            product_depth_backlog_path=args.product_depth_backlog,
            product_depth_selection_path=args.product_depth_selection,
            host_onboarding_depth_plan_path=args.host_onboarding_depth_plan,
            review_agent_v3_plan_path=args.review_agent_v3_plan,
            dataset_quality_depth_plan_path=args.dataset_quality_depth_plan,
            distribution_rollout_packet_path=args.distribution_rollout_packet,
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


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=None, help="Optional release tag, for example v1.10.0.")
    parser.add_argument("--manual-runs", type=Path, default=_DEFAULT_MANUAL_RUNS_PATH)
    parser.add_argument("--host-report-root", type=Path, default=Path())
    parser.add_argument("--host-report", type=Path, default=None)
    parser.add_argument("--v1-decision-report", type=Path, default=_DEFAULT_V1_DECISION_REPORT_PATH)
    parser.add_argument("--v1-evidence-operator-packet", type=Path, default=_DEFAULT_V1_EVIDENCE_OPERATOR_PACKET_PATH)
    parser.add_argument("--v1-growth-cutover-report", type=Path, default=_DEFAULT_V1_GROWTH_CUTOVER_REPORT_PATH)
    parser.add_argument("--v1-stabilization-plan", type=Path, default=_DEFAULT_V1_STABILIZATION_PLAN_PATH)
    parser.add_argument("--v1-rc-readiness-report", type=Path, default=_DEFAULT_V1_RC_READINESS_REPORT_PATH)
    parser.add_argument("--p0-host-runbook", type=Path, default=_DEFAULT_P0_HOST_RUNBOOK_PATH)
    parser.add_argument("--p0-host-run-session", type=Path, default=_DEFAULT_P0_HOST_RUN_SESSION_PATH)
    parser.add_argument("--p0-evidence-recorder", type=Path, default=_DEFAULT_P0_EVIDENCE_RECORDER_PATH)
    parser.add_argument("--p0-evidence-import-guide", type=Path, default=_DEFAULT_P0_EVIDENCE_IMPORT_GUIDE_PATH)
    parser.add_argument(
        "--p0-evidence-regeneration-pack",
        type=Path,
        default=_DEFAULT_P0_EVIDENCE_REGENERATION_PACK_PATH,
    )
    parser.add_argument("--p0-host-execution-sprint", type=Path, default=_DEFAULT_P0_HOST_EXECUTION_SPRINT_PATH)
    parser.add_argument("--p0-host-evidence-ledger", type=Path, default=_DEFAULT_P0_HOST_EVIDENCE_LEDGER_PATH)
    parser.add_argument("--p0-evidence-status", type=Path, default=_DEFAULT_P0_EVIDENCE_STATUS_PATH)
    parser.add_argument("--p0-blocker-triage", type=Path, default=_DEFAULT_P0_BLOCKER_TRIAGE_PATH)
    parser.add_argument("--p0-host-unblock-pack", type=Path, default=_DEFAULT_P0_HOST_UNBLOCK_PACK_PATH)
    parser.add_argument("--p0-host-evidence-recovery", type=Path, default=_DEFAULT_P0_HOST_EVIDENCE_RECOVERY_PATH)
    parser.add_argument("--host-evidence-runner", type=Path, default=_DEFAULT_HOST_EVIDENCE_RUNNER_PATH)
    parser.add_argument("--codex-cancellation-triage", type=Path, default=_DEFAULT_CODEX_CANCELLATION_TRIAGE_PATH)
    parser.add_argument("--claude-code-setup-path", type=Path, default=_DEFAULT_CLAUDE_CODE_SETUP_PATH)
    parser.add_argument("--host-setup-probe", type=Path, default=_DEFAULT_HOST_SETUP_PROBE_PATH)
    parser.add_argument("--beta-campaign-pack", type=Path, default=_DEFAULT_BETA_CAMPAIGN_PACK_PATH)
    parser.add_argument("--beta-campaign-execution", type=Path, default=_DEFAULT_BETA_CAMPAIGN_EXECUTION_PATH)
    parser.add_argument("--beta-feedback-intake", type=Path, default=_DEFAULT_BETA_FEEDBACK_INTAKE_PATH)
    parser.add_argument("--beta-feedback-status", type=Path, default=_DEFAULT_BETA_FEEDBACK_STATUS_PATH)
    parser.add_argument("--beta-to-backlog-triage", type=Path, default=_DEFAULT_BETA_TO_BACKLOG_TRIAGE_PATH)
    parser.add_argument("--beta-validation-intake", type=Path, default=_DEFAULT_BETA_VALIDATION_INTAKE_PATH)
    parser.add_argument(
        "--beta-validation-recording-pack",
        type=Path,
        default=_DEFAULT_BETA_VALIDATION_RECORDING_PACK_PATH,
    )
    parser.add_argument("--beta-validation-sprint", type=Path, default=_DEFAULT_BETA_VALIDATION_SPRINT_PATH)
    _add_v1_rc_doc_arguments(parser)
    parser.add_argument("--product-depth-backlog", type=Path, default=_DEFAULT_PRODUCT_DEPTH_BACKLOG_PATH)
    parser.add_argument("--product-depth-selection", type=Path, default=_DEFAULT_PRODUCT_DEPTH_SELECTION_PATH)
    parser.add_argument("--host-onboarding-depth-plan", type=Path, default=_DEFAULT_HOST_ONBOARDING_DEPTH_PLAN_PATH)
    parser.add_argument("--review-agent-v3-plan", type=Path, default=_DEFAULT_REVIEW_AGENT_V3_PLAN_PATH)
    parser.add_argument("--dataset-quality-depth-plan", type=Path, default=_DEFAULT_DATASET_QUALITY_DEPTH_PLAN_PATH)
    parser.add_argument("--distribution-rollout-packet", type=Path, default=_DEFAULT_DISTRIBUTION_ROLLOUT_PACKET_PATH)
    parser.add_argument("--mcp-snapshot", type=Path, default=_DEFAULT_MCP_SNAPSHOT_PATH)
    parser.add_argument("--output-snapshot", type=Path, default=_DEFAULT_OUTPUT_SNAPSHOT_PATH)
    parser.add_argument("--contract-output-work-dir", type=Path, default=None)
    parser.add_argument("--pyproject", type=Path, default=_DEFAULT_PYPROJECT_PATH)
    parser.add_argument("--server-json", type=Path, default=_DEFAULT_SERVER_JSON_PATH)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def _add_v1_rc_doc_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--v1-rc-release-packet", type=Path, default=_DEFAULT_V1_RC_RELEASE_PACKET_PATH)
    parser.add_argument("--v1-rc-cutover-checklist", type=Path, default=_DEFAULT_V1_RC_CUTOVER_CHECKLIST_PATH)
    parser.add_argument("--v1-rc-automation-pack", type=Path, default=_DEFAULT_V1_RC_AUTOMATION_PACK_PATH)
    parser.add_argument("--v1-rc-rehearsal-plan", type=Path, default=_DEFAULT_V1_RC_REHEARSAL_PLAN_PATH)
    parser.add_argument("--v1-rc-cutover-gate", type=Path, default=_DEFAULT_V1_RC_CUTOVER_GATE_PATH)
    parser.add_argument("--rc-cutover-recovery-plan", type=Path, default=_DEFAULT_RC_CUTOVER_RECOVERY_PLAN_PATH)
    parser.add_argument("--rc-dry-run", type=Path, default=_DEFAULT_RC_DRY_RUN_PATH)
    parser.add_argument("--rc-gate-reopen-packet", type=Path, default=_DEFAULT_RC_GATE_REOPEN_PACKET_PATH)


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


def _check_p0_host_run_preflight() -> ReleaseReadinessCheck:
    report = check_p0_host_run_preflight()
    failed = [check for check in report.checks if not check.ok]
    if failed:
        return ReleaseReadinessCheck(
            name="p0_host_run_preflight",
            ok=False,
            message="; ".join(f"{check.name}: {check.message}" for check in failed),
        )
    return ReleaseReadinessCheck(
        name="p0_host_run_preflight",
        ok=True,
        message=f"p0 host run preflight is valid ({len(report.checks)} checks)",
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
