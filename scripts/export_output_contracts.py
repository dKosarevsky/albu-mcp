"""Export deterministic representative output contract snapshots."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from albumentationsx_mcp.dataset import score_dataset_preview_candidates
from albumentationsx_mcp.diagnostics import DiagnosticsService, PublicSurface
from albumentationsx_mcp.models import (
    DatasetPreviewScore,
    ImageQualityAggregate,
    PreviewFeedbackRecord,
    PreviewManifestSummary,
    PreviewQualitySummary,
    PreviewRunComparison,
    QualityFinding,
    TuningDecisionRecord,
    TuningSessionSummary,
)
from albumentationsx_mcp.recipes import recommend_recipe
from albumentationsx_mcp.reports import PreviewReportService
from albumentationsx_mcp.review import PreviewFeedbackStore

_REPORT_UUID_PATTERN = re.compile(r"preview-report-baseline-[0-9a-f]{32}\.(md|html)")


def build_output_contract_snapshot(root: Path) -> dict[str, Any]:
    """Build representative response payloads with unstable values normalized."""
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    feedback_store = PreviewFeedbackStore(root / "feedback")
    feedback = feedback_store.record_feedback(
        run_id="candidate-a",
        image_index=7,
        variant_index=0,
        feedback_tags=["too_noisy:high"],
        note="example 8 is too noisy",
        accepted=False,
    )
    listing = feedback_store.list_feedback(run_id="candidate-a", limit=5)
    report = PreviewReportService(root / "artifacts").export_report(
        _dataset_score(),
        baseline_manifest=_manifest(root, "baseline"),
        candidate_manifests=[_manifest(root, "candidate-a"), _manifest(root, "candidate-b")],
        decisions=[_decision()],
        feedback_records=[feedback],
        output_format="markdown",
    )
    return {
        "snapshot": {"version": 1},
        "recommend_recipe": recommend_recipe("ocr", intensity="low").model_dump(mode="json"),
        "diagnose_environment_ok": _diagnostics_ok(root),
        "diagnose_environment_missing_allowed_root": _diagnostics_missing_allowed_root(root),
        "score_dataset_preview_candidates": _dataset_score().model_dump(mode="json"),
        "record_preview_feedback": _normalize_feedback_record(feedback),
        "list_preview_feedback": {
            **listing.model_dump(mode="json"),
            "feedback": [_normalize_feedback_record(item) for item in listing.feedback],
        },
        "export_preview_report": _normalize_report_export(report.model_dump(mode="json"), root, feedback),
    }


def dump_output_contract_snapshot(snapshot: dict[str, Any]) -> str:
    """Serialize output contract snapshots with stable formatting."""
    return json.dumps(_json_safe(snapshot), indent=2, sort_keys=True) + "\n"


def main() -> None:
    """Write representative output contract snapshots to stdout or a file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional path to write the snapshot JSON.")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="albu-output-contracts-") as tmp_dir:
        content = dump_output_contract_snapshot(build_output_contract_snapshot(Path(tmp_dir)))
    if args.output is None:
        sys.stdout.write(content)
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _dataset_score() -> DatasetPreviewScore:
    return score_dataset_preview_candidates(
        [
            _comparison("candidate-a", brightness=128.0, clipping=0.02, findings=[]),
            _comparison(
                "candidate-b",
                brightness=78.0,
                clipping=0.18,
                findings=[
                    QualityFinding(
                        code="candidate_high_clipping",
                        severity="medium",
                        message="Candidate preview has noticeable clipped dark or bright pixels.",
                        metric="clipping_fraction",
                        value=0.18,
                        baseline_value=0.01,
                    ),
                ],
            ),
        ],
        feedback_tags_by_candidate={"candidate-a": ["too_noisy:low"], "candidate-b": ["too_blurry:high"]},
        accepted_candidate_ids={"candidate-a"},
        quality_profile="classification",
    )


def _comparison(
    candidate_run_id: str,
    *,
    brightness: float,
    clipping: float,
    findings: list[QualityFinding],
) -> PreviewRunComparison:
    return PreviewRunComparison(
        baseline=_summary("baseline"),
        candidate=_summary(candidate_run_id),
        pipeline_changed=True,
        inputs_changed=False,
        seed_changed=False,
        artifact_count_delta=0,
        review_notes=["Review rendered contact sheets."],
        suggested_feedback_tags=["too_noisy"],
        quality_summary=PreviewQualitySummary(
            quality_profile="classification",
            baseline=ImageQualityAggregate(image_count=2, brightness_mean=120.0, clipping_fraction=0.01),
            candidate=ImageQualityAggregate(image_count=2, brightness_mean=brightness, clipping_fraction=clipping),
            findings=findings,
        ),
    )


def _summary(run_id: str) -> PreviewManifestSummary:
    return PreviewManifestSummary(
        run_id=run_id,
        created_at="2026-06-14T12:00:00Z",
        input_count=2,
        variants_per_image=1,
        seed=137,
        transform_count=1,
        transform_names=["RandomBrightnessContrast"],
    )


def _manifest(root: Path, run_id: str) -> dict[str, object]:
    contact_sheet = root / "images" / f"{run_id}-contact.png"
    return {
        "run_id": run_id,
        "summary": {
            "contact_sheet_paths": [str(contact_sheet)],
        },
        "artifacts": [
            {
                "kind": "contact_sheet",
                "path": str(contact_sheet),
            },
        ],
    }


def _decision() -> TuningDecisionRecord:
    summary = TuningSessionSummary(
        baseline_run_id="baseline",
        candidate_run_id="candidate-a",
        feedback_tags=["too_noisy:low"],
        accepted=True,
        export_ready=True,
        recommended_next_tool="export_pipeline",
        rationale="accepted",
        quality_score=100.0,
        quality_risk="low",
    )
    return TuningDecisionRecord(
        decision_id="decision-a",
        created_at="2026-06-14T12:05:00Z",
        baseline_run_id="baseline",
        candidate_run_id="candidate-a",
        feedback_tags=["too_noisy:low"],
        accepted=True,
        export_ready=True,
        recommended_next_tool="export_pipeline",
        quality_score=100.0,
        quality_risk="low",
        reviewer_notes=["accepted output contract fixture"],
        summary=summary,
    )


def _diagnostics_ok(root: Path) -> dict[str, Any]:
    images_root = root / "diagnostics" / "images"
    images_root.mkdir(parents=True)
    report = DiagnosticsService(
        allowed_roots=[images_root],
        artifact_root=root / "diagnostics" / "artifacts",
        max_preview_runs=7,
        public_surface=_diagnostics_public_surface(),
    ).diagnose(include_write_probe=True)
    return _normalize_diagnostics_report(report.model_dump(mode="json"), root)


def _diagnostics_missing_allowed_root(root: Path) -> dict[str, Any]:
    report = DiagnosticsService(
        allowed_roots=[root / "diagnostics" / "missing-images"],
        artifact_root=root / "diagnostics-missing-root" / "artifacts",
        max_preview_runs=100,
        public_surface=_diagnostics_public_surface(),
    ).diagnose(include_write_probe=False)
    return _normalize_diagnostics_report(report.model_dump(mode="json"), root)


def _diagnostics_public_surface() -> PublicSurface:
    return PublicSurface(
        tools=[
            "search_transforms",
            "get_transform_schema",
            "validate_pipeline",
            "recommend_pipeline",
            "adjust_pipeline",
            "explain_pipeline",
            "list_feedback_tags",
            "render_preview",
            "render_preview_batch",
            "compare_preview_runs",
            "summarize_tuning_session",
            "rank_preview_candidates",
            "score_dataset_preview_candidates",
            "list_quality_profiles",
            "recommend_recipe",
            "record_preview_feedback",
            "list_preview_feedback",
            "record_tuning_decision",
            "list_tuning_decisions",
            "export_tuning_report",
            "export_preview_report",
            "list_preview_runs",
            "get_preview_manifest",
            "delete_preview_run",
            "cleanup_preview_runs",
            "export_pipeline",
            "diagnose_environment",
            "run_host_smoke_check",
        ],
        prompts=[
            "build_robustness_augmentation_session",
            "compare_preview_runs_for_feedback",
            "tune_pipeline_from_preview_feedback",
            "export_reproducible_pipeline",
        ],
        workflow_resources=[
            "albumentationsx://workflows/catalog",
            "albumentationsx://workflows/preview-tuning",
            "albumentationsx://workflows/annotation-preview",
            "albumentationsx://workflows/task-profiles",
            "albumentationsx://recipes/catalog",
            "albumentationsx://diagnostics/guide",
            "albumentationsx://examples/client-smoke",
            "albumentationsx://examples/diagnostics",
            "albumentationsx://examples/review-loop",
            "albumentationsx://examples/report-handoff",
        ],
    )


def _normalize_feedback_record(record: PreviewFeedbackRecord) -> dict[str, Any]:
    payload = record.model_dump(mode="json")
    payload["feedback_id"] = "<feedback-id>"
    payload["created_at"] = "<created-at>"
    return payload


def _normalize_diagnostics_report(payload: dict[str, Any], root: Path) -> dict[str, Any]:
    normalized = _normalize_paths(payload, root)
    normalized["environment"]["albumentationsx_version"] = "<albumentationsx-version>"
    for check in normalized["checks"]:
        if check["code"] == "albumentationsx_import":
            check["details"]["module_version"] = "<albumentationsx-version>"
            check["details"]["package_version"] = "<albumentationsx-version>"
    return normalized


def _normalize_report_export(payload: dict[str, Any], root: Path, feedback: PreviewFeedbackRecord) -> dict[str, Any]:
    normalized = _normalize_paths(payload, root)
    normalized["content"] = normalized["content"].replace(feedback.feedback_id, "<feedback-id>")
    normalized["content"] = _REPORT_UUID_PATTERN.sub(r"preview-report-baseline.<\1>", normalized["content"])
    normalized["artifact"] = {
        **normalized["artifact"],
        "uri": "artifact://reports/preview-report-baseline.<md>",
        "path": "<artifact-path>",
        "sha256": "<sha256>",
        "size_bytes": "<size-bytes>",
    }
    return normalized


def _normalize_paths(value: Any, root: Path) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_paths(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_paths(item, root) for item in value]
    if isinstance(value, str):
        return value.replace(str(root), "<OUTPUT_CONTRACT_ROOT>").replace(
            root.resolve().as_uri(),
            "file://<OUTPUT_CONTRACT_ROOT>",
        )
    return value


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
