"""FastMCP preview, review, ranking, and report registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface, ProfileSurface
from albumentationsx_mcp.capabilities import REVIEW_DATASET_PROFILE_MEMBERSHIP, REVIEW_PROFILE_MEMBERSHIP
from albumentationsx_mcp.dataset import score_dataset_preview_candidates as score_dataset_candidates
from albumentationsx_mcp.mcp_app import (
    PREVIEW_ARTIFACT_URI_TEMPLATE,
    PREVIEW_REVIEW_APP_URI,
    preview_review_tool_meta,
    register_preview_review_resources,
)
from albumentationsx_mcp.models import (
    ArtifactRef,
    InteractiveTuningSession,
    PreviewFeedbackRecord,
    PreviewRequest,
    QualityProfileName,
    TargetSpec,
)
from albumentationsx_mcp.ranking import rank_preview_candidates as rank_candidates
from albumentationsx_mcp.review_agent import build_review_agent_plan
from albumentationsx_mcp.review_agent import interpret_preview_feedback as interpret_feedback_note

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from albumentationsx_mcp.preview import ArtifactStore, PreviewService
    from albumentationsx_mcp.preview_validation import PreviewRequestValidator
    from albumentationsx_mcp.reports import PreviewReportService
    from albumentationsx_mcp.review import PreviewFeedbackStore
    from albumentationsx_mcp.sessions import InteractiveTuningSessionStore
    from albumentationsx_mcp.tuning import TuningDecisionStore

_TOOLS = (
    "validate_preview_request",
    "render_preview",
    "render_preview_batch",
    "compare_preview_runs",
    "interpret_preview_feedback",
    "plan_preview_review",
    "rank_preview_candidates",
    "export_preview_report",
)
_DATASET_TOOLS = (
    "validate_preview_request",
    "render_preview_batch",
    "compare_preview_runs",
    "export_preview_report",
)
_REVIEW_ONLY_TOOLS = tuple(tool for tool in _TOOLS if tool not in _DATASET_TOOLS)
_RESOURCES = (PREVIEW_REVIEW_APP_URI,)
_RESOURCE_TEMPLATES = (PREVIEW_ARTIFACT_URI_TEMPLATE,)
SURFACE = AdapterSurface(
    adapter="preview",
    tools=_TOOLS,
    resources=_RESOURCES,
    resource_templates=_RESOURCE_TEMPLATES,
    profile_surfaces=(
        ProfileSurface(profiles=REVIEW_PROFILE_MEMBERSHIP, tools=_REVIEW_ONLY_TOOLS),
        ProfileSurface(
            profiles=REVIEW_DATASET_PROFILE_MEMBERSHIP,
            tools=_DATASET_TOOLS,
            resources=_RESOURCES,
            resource_templates=_RESOURCE_TEMPLATES,
        ),
    ),
)


def register_preview_adapter(  # noqa: PLR0913
    mcp: FastMCP,
    *,
    artifact_store: ArtifactStore,
    preview_service: PreviewService,
    preview_validator: PreviewRequestValidator,
    tuning_store: TuningDecisionStore,
    session_store: InteractiveTuningSessionStore,
    feedback_store: PreviewFeedbackStore,
    report_service: PreviewReportService,
) -> None:
    """Register preview rendering, review, ranking, reports, and MCP App resources."""
    register_preview_review_resources(mcp, artifact_store)

    @mcp.tool(name="validate_preview_request")
    def validate_preview_request_tool(request: dict[str, Any], target: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate a preview request before rendering local preview artifacts."""
        target_spec = TargetSpec.model_validate(target or {})
        return preview_validator.validate(request, target=target_spec).model_dump(mode="json")

    @mcp.tool(meta=preview_review_tool_meta())
    def render_preview(request: dict[str, Any]) -> dict[str, Any]:
        """Render deterministic preview artifacts for local input images."""
        preview_request = PreviewRequest.model_validate(request)
        return preview_service.render_preview(preview_request).model_dump(mode="json")

    @mcp.tool(meta=preview_review_tool_meta())
    def render_preview_batch(request: dict[str, Any]) -> dict[str, Any]:
        """Render deterministic batch preview artifacts and contact sheets for local input images."""
        preview_request = PreviewRequest.model_validate(request)
        return preview_service.render_preview(preview_request).model_dump(mode="json")

    @mcp.tool()
    def compare_preview_runs(
        baseline_run_id: str,
        candidate_run_id: str,
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Compare two preview manifests to guide structured feedback and reproducible tuning."""
        return preview_service.compare_preview_runs(
            baseline_run_id,
            candidate_run_id,
            quality_profile=quality_profile,
        ).model_dump(mode="json")

    @mcp.tool()
    def interpret_preview_feedback(feedback_note: str) -> dict[str, Any]:
        """Convert free-form preview feedback into structured feedback tags."""
        return interpret_feedback_note(feedback_note).model_dump(mode="json")

    @mcp.tool()
    def plan_preview_review(  # noqa: PLR0913
        baseline_run_id: str,
        candidate_run_id: str,
        feedback_tags: list[str] | None = None,
        feedback_note: str | None = None,
        accepted: bool = False,  # noqa: FBT001, FBT002
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Plan the next review action for one baseline-to-candidate preview comparison."""
        comparison = preview_service.compare_preview_runs(
            baseline_run_id,
            candidate_run_id,
            quality_profile=quality_profile,
        )
        return build_review_agent_plan(
            comparison,
            feedback_tags=feedback_tags or [],
            feedback_note=feedback_note,
            accepted=accepted,
        ).model_dump(mode="json")

    @mcp.tool()
    def rank_preview_candidates(
        baseline_run_id: str,
        candidate_run_ids: list[str],
        feedback_tags_by_candidate: dict[str, list[str]] | None = None,
        accepted_candidate_ids: list[str] | None = None,
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Rank multiple candidate preview runs against one baseline."""
        if not candidate_run_ids:
            msg = "candidate_run_ids must contain at least one run id"
            raise ValueError(msg)
        comparisons = [
            preview_service.compare_preview_runs(
                baseline_run_id,
                candidate_run_id,
                quality_profile=quality_profile,
            )
            for candidate_run_id in candidate_run_ids[:20]
        ]
        return rank_candidates(
            comparisons,
            feedback_tags_by_candidate=feedback_tags_by_candidate or {},
            accepted_candidate_ids=set(accepted_candidate_ids or []),
            quality_profile=quality_profile,
        ).model_dump(mode="json")

    @mcp.tool()
    def export_preview_report(  # noqa: PLR0913
        baseline_run_id: str,
        candidate_run_ids: list[str],
        output_format: Literal["markdown", "html"] = "markdown",
        feedback_tags_by_candidate: dict[str, list[str]] | None = None,
        accepted_candidate_ids: list[str] | None = None,
        quality_profile: QualityProfileName = "balanced",
        include_decisions: bool = True,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """Export a visual preview report with ranking, contact sheets, and decisions."""
        if not candidate_run_ids:
            msg = "candidate_run_ids must contain at least one run id"
            raise ValueError(msg)
        bounded_candidate_ids = candidate_run_ids[:20]
        comparisons = [
            preview_service.compare_preview_runs(
                baseline_run_id,
                candidate_run_id,
                quality_profile=quality_profile,
            )
            for candidate_run_id in bounded_candidate_ids
        ]
        score = score_dataset_candidates(
            comparisons,
            feedback_tags_by_candidate=feedback_tags_by_candidate or {},
            accepted_candidate_ids=set(accepted_candidate_ids or []),
            quality_profile=quality_profile,
        )
        tuning_sessions = _matching_tuning_sessions(
            session_store,
            baseline_run_id=baseline_run_id,
            candidate_run_ids=set(bounded_candidate_ids),
        )
        return report_service.export_report(
            score,
            baseline_manifest=preview_service.artifact_store.read_manifest(baseline_run_id),
            candidate_manifests=[
                preview_service.artifact_store.read_manifest(candidate_run_id)
                for candidate_run_id in bounded_candidate_ids
            ],
            decisions=_matching_tuning_decisions(
                tuning_store,
                baseline_run_id=baseline_run_id,
                candidate_run_ids=set(bounded_candidate_ids),
                include_decisions=include_decisions,
            ),
            feedback_records=_matching_preview_feedback(
                feedback_store,
                run_ids={baseline_run_id, *bounded_candidate_ids},
            ),
            tuning_sessions=tuning_sessions,
            tuning_session_artifacts=_export_tuning_session_artifacts(session_store, tuning_sessions),
            output_format=output_format,
        ).model_dump(mode="json")


def _matching_tuning_decisions(
    tuning_store: TuningDecisionStore,
    *,
    baseline_run_id: str,
    candidate_run_ids: set[str],
    include_decisions: bool,
) -> list[Any]:
    if not include_decisions:
        return []
    decisions = tuning_store.list_decisions(limit=100, ranked=True).decisions
    return [
        decision
        for decision in decisions
        if decision.baseline_run_id == baseline_run_id and decision.candidate_run_id in candidate_run_ids
    ]


def _matching_preview_feedback(
    feedback_store: PreviewFeedbackStore,
    *,
    run_ids: set[str],
) -> list[PreviewFeedbackRecord]:
    records: list[PreviewFeedbackRecord] = []
    for run_id in sorted(run_ids):
        records.extend(feedback_store.list_feedback(run_id=run_id, limit=100).feedback)
    return sorted(records, key=lambda record: record.created_at, reverse=True)


def _matching_tuning_sessions(
    session_store: InteractiveTuningSessionStore,
    *,
    baseline_run_id: str,
    candidate_run_ids: set[str],
) -> list[InteractiveTuningSession]:
    sessions = session_store.list_sessions(limit=100).sessions
    return [
        session
        for session in sessions
        if session.baseline_run_id == baseline_run_id
        and (
            session.accepted_candidate_run_id in candidate_run_ids
            or any(step.candidate_run_id in candidate_run_ids for step in session.steps)
        )
    ]


def export_matching_tuning_session_artifacts(
    session_store: InteractiveTuningSessionStore,
    *,
    baseline_run_id: str,
    candidate_run_ids: set[str],
) -> list[ArtifactRef]:
    """Export matching session artifacts for compatibility and report assembly."""
    return _export_tuning_session_artifacts(
        session_store,
        _matching_tuning_sessions(
            session_store,
            baseline_run_id=baseline_run_id,
            candidate_run_ids=candidate_run_ids,
        ),
    )


def _export_tuning_session_artifacts(
    session_store: InteractiveTuningSessionStore,
    sessions: list[InteractiveTuningSession],
) -> list[ArtifactRef]:
    return [session_store.export_session(session.session_id, output_format="markdown").artifact for session in sessions]
