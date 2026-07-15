"""FastMCP tuning session, feedback, decision, and retention registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface
from albumentationsx_mcp.models import QualityProfileName
from albumentationsx_mcp.tuning import build_tuning_session_summary

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from albumentationsx_mcp.preview import PreviewService
    from albumentationsx_mcp.review import PreviewFeedbackStore
    from albumentationsx_mcp.sessions import InteractiveTuningSessionStore
    from albumentationsx_mcp.tuning import TuningDecisionStore

SURFACE = AdapterSurface(
    adapter="sessions",
    tools=(
        "summarize_tuning_session",
        "start_tuning_session",
        "record_tuning_session_step",
        "list_tuning_sessions",
        "export_tuning_session",
        "close_tuning_session",
        "archive_tuning_session",
        "cleanup_tuning_sessions",
        "record_preview_feedback",
        "list_preview_feedback",
        "record_tuning_decision",
        "list_tuning_decisions",
        "export_tuning_report",
        "list_preview_runs",
        "get_preview_manifest",
        "delete_preview_run",
        "cleanup_preview_runs",
    ),
)


def register_session_adapter(
    mcp: FastMCP,
    *,
    preview_service: PreviewService,
    tuning_store: TuningDecisionStore,
    session_store: InteractiveTuningSessionStore,
    feedback_store: PreviewFeedbackStore,
) -> None:
    """Register tuning persistence, feedback, decisions, and preview retention."""

    @mcp.tool()
    def summarize_tuning_session(
        baseline_run_id: str,
        candidate_run_id: str,
        feedback_tags: list[str] | None = None,
        accepted: bool = False,  # noqa: FBT001, FBT002
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Summarize a baseline-to-candidate preview tuning step."""
        comparison = preview_service.compare_preview_runs(
            baseline_run_id,
            candidate_run_id,
            quality_profile=quality_profile,
        )
        return build_tuning_session_summary(
            comparison,
            feedback_tags=feedback_tags or [],
            accepted=accepted,
        ).model_dump(mode="json")

    @mcp.tool()
    def start_tuning_session(
        task: str,
        targets: list[str] | None = None,
        baseline_run_id: str | None = None,
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Start a persistent multi-step preview tuning session."""
        if baseline_run_id is not None:
            preview_service.artifact_store.read_manifest(baseline_run_id)
        return session_store.start_session(
            task=task,
            targets=targets or ["image"],
            baseline_run_id=baseline_run_id,
            quality_profile=quality_profile,
        ).model_dump(mode="json")

    @mcp.tool()
    def record_tuning_session_step(  # noqa: PLR0913
        session_id: str,
        baseline_run_id: str,
        candidate_run_id: str,
        feedback_tags: list[str] | None = None,
        accepted: bool = False,  # noqa: FBT001, FBT002
        reviewer_notes: list[str] | None = None,
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Record one candidate comparison inside an interactive tuning session."""
        comparison = preview_service.compare_preview_runs(
            baseline_run_id,
            candidate_run_id,
            quality_profile=quality_profile,
        )
        summary = build_tuning_session_summary(
            comparison,
            feedback_tags=feedback_tags or [],
            accepted=accepted,
        )
        return session_store.record_step(
            session_id,
            summary=summary,
            reviewer_notes=reviewer_notes,
        ).model_dump(mode="json")

    @mcp.tool()
    def list_tuning_sessions(
        limit: int = 20,
        status: Literal["active", "accepted", "rejected", "archived"] | None = None,
    ) -> dict[str, Any]:
        """List persisted interactive preview tuning sessions."""
        return session_store.list_sessions(limit=limit, status=status).model_dump(mode="json")

    @mcp.tool()
    def export_tuning_session(
        session_id: str,
        output_format: Literal["markdown", "json"] = "markdown",
    ) -> dict[str, Any]:
        """Export one interactive tuning session as Markdown or JSON."""
        return session_store.export_session(session_id, output_format=output_format).model_dump(mode="json")

    @mcp.tool()
    def close_tuning_session(
        session_id: str,
        status: Literal["accepted", "rejected"],
        accepted_candidate_run_id: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Close an interactive tuning session as accepted or rejected."""
        return session_store.close_session(
            session_id,
            status=status,
            accepted_candidate_run_id=accepted_candidate_run_id,
            note=note,
        ).model_dump(mode="json")

    @mcp.tool()
    def archive_tuning_session(session_id: str, note: str | None = None) -> dict[str, Any]:
        """Archive an interactive tuning session without deleting its audit trail."""
        return session_store.archive_session(session_id, note=note).model_dump(mode="json")

    @mcp.tool()
    def cleanup_tuning_sessions(
        keep_last: int = 100,
        include_active: bool = False,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """Delete older interactive tuning sessions, protecting active sessions by default."""
        return session_store.cleanup_sessions(keep_last=keep_last, include_active=include_active).model_dump(
            mode="json"
        )

    @mcp.tool()
    def record_preview_feedback(  # noqa: PLR0913
        run_id: str,
        image_index: int,
        variant_index: int,
        feedback_tags: list[str] | None = None,
        note: str = "",
        accepted: bool = False,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """Persist user feedback for one concrete preview image variant."""
        manifest = preview_service.artifact_store.read_manifest(run_id)
        _validate_feedback_target(manifest, image_index=image_index, variant_index=variant_index)
        return feedback_store.record_feedback(
            run_id=run_id,
            image_index=image_index,
            variant_index=variant_index,
            feedback_tags=feedback_tags or [],
            note=note,
            accepted=accepted,
        ).model_dump(mode="json")

    @mcp.tool()
    def list_preview_feedback(
        run_id: str | None = None,
        limit: int = 20,
        accepted_only: bool = False,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """List concrete preview feedback records."""
        return feedback_store.list_feedback(
            run_id=run_id,
            limit=limit,
            accepted_only=accepted_only,
        ).model_dump(mode="json")

    @mcp.tool()
    def record_tuning_decision(  # noqa: PLR0913
        baseline_run_id: str,
        candidate_run_id: str,
        feedback_tags: list[str] | None = None,
        accepted: bool = False,  # noqa: FBT001, FBT002
        reviewer_notes: list[str] | None = None,
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Persist a local tuning decision for one preview comparison."""
        comparison = preview_service.compare_preview_runs(
            baseline_run_id,
            candidate_run_id,
            quality_profile=quality_profile,
        )
        summary = build_tuning_session_summary(
            comparison,
            feedback_tags=feedback_tags or [],
            accepted=accepted,
        )
        return tuning_store.record_decision(summary, reviewer_notes).model_dump(mode="json")

    @mcp.tool()
    def list_tuning_decisions(
        limit: int = 20,
        accepted_only: bool = False,  # noqa: FBT001, FBT002
        ranked: bool = False,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """List persisted local tuning decisions."""
        return tuning_store.list_decisions(limit=limit, accepted_only=accepted_only, ranked=ranked).model_dump(
            mode="json"
        )

    @mcp.tool()
    def export_tuning_report(
        output_format: Literal["markdown", "json"] = "markdown",
        limit: int = 20,
        accepted_only: bool = False,  # noqa: FBT001, FBT002
        ranked: bool = True,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """Export persisted tuning decisions as markdown or JSON."""
        return tuning_store.export_report(
            output_format=output_format,
            limit=limit,
            accepted_only=accepted_only,
            ranked=ranked,
        ).model_dump(mode="json")

    @mcp.tool()
    def list_preview_runs(limit: int = 20) -> dict[str, Any]:
        """List recent preview runs recorded under the configured artifact root."""
        bounded_limit = max(1, min(limit, 100))
        return {
            "runs": [run.model_dump(mode="json") for run in preview_service.artifact_store.list_runs(bounded_limit)]
        }

    @mcp.tool()
    def get_preview_manifest(run_id: str) -> dict[str, Any]:
        """Return the manifest JSON for one recorded preview run."""
        return preview_service.artifact_store.read_manifest(run_id)

    @mcp.tool()
    def delete_preview_run(run_id: str) -> dict[str, Any]:
        """Delete one preview run and its artifacts from the configured artifact root."""
        deleted = preview_service.artifact_store.delete_run(run_id)
        return {"deleted": deleted.model_dump(mode="json")}

    @mcp.tool()
    def cleanup_preview_runs(keep_last: int | None = None) -> dict[str, Any]:
        """Delete older preview runs beyond a retention count."""
        deleted = preview_service.artifact_store.cleanup_runs(keep_last)
        return {"deleted_runs": [run.model_dump(mode="json") for run in deleted]}


def _validate_feedback_target(manifest: dict[str, Any], *, image_index: int, variant_index: int) -> None:
    summary = manifest.get("summary", {})
    input_count = int(summary.get("input_count", len(manifest.get("inputs", []))))
    variants_per_image = int(summary.get("variants_per_image", 1))
    if image_index < 0 or image_index >= input_count:
        msg = f"image_index must be between 0 and {max(input_count - 1, 0)}"
        raise ValueError(msg)
    if variant_index < 0 or variant_index >= variants_per_image:
        msg = f"variant_index must be between 0 and {max(variants_per_image - 1, 0)}"
        raise ValueError(msg)
