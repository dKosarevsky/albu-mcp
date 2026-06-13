from pathlib import Path

from albumentationsx_mcp.dataset import score_dataset_preview_candidates
from albumentationsx_mcp.models import (
    ImageQualityAggregate,
    PreviewManifestSummary,
    PreviewQualitySummary,
    PreviewRunComparison,
    TuningDecisionRecord,
    TuningSessionSummary,
)
from albumentationsx_mcp.reports import PreviewReportService


def test_preview_report_service_exports_markdown_artifact_with_decision_trail(tmp_path: Path) -> None:
    baseline_sheet = tmp_path / "baseline.png"
    candidate_sheet = tmp_path / "candidate-a.png"
    baseline_sheet.write_bytes(b"baseline")
    candidate_sheet.write_bytes(b"candidate")
    score = _score("candidate-a")
    decision = _decision("decision-a", "candidate-a")

    report = PreviewReportService(tmp_path / "artifacts").export_report(
        score,
        baseline_manifest=_manifest("baseline", baseline_sheet),
        candidate_manifests=[_manifest("candidate-a", candidate_sheet)],
        decisions=[decision],
        output_format="markdown",
    )

    artifact_path = Path(report.artifact.path)
    assert report.format == "markdown"
    assert report.baseline_run_id == "baseline"
    assert report.best_candidate_run_id == "candidate-a"
    assert report.candidate_count == 1
    assert report.artifact.kind == "report"
    assert artifact_path.parent.name == "reports"
    assert artifact_path.suffix == ".md"
    assert artifact_path.exists()
    assert artifact_path.read_text(encoding="utf-8") == report.content
    assert "# AlbumentationsX MCP Preview Report" in report.content
    assert str(baseline_sheet) in report.content
    assert str(candidate_sheet) in report.content
    assert "decision-a" in report.content


def test_preview_report_service_exports_html_with_escaped_dynamic_text(tmp_path: Path) -> None:
    contact_sheet = tmp_path / "candidate.png"
    contact_sheet.write_bytes(b"candidate")
    candidate_id = "candidate-<script>"
    score = _score(candidate_id)

    report = PreviewReportService(tmp_path / "artifacts").export_report(
        score,
        baseline_manifest=_manifest("baseline", contact_sheet),
        candidate_manifests=[_manifest(candidate_id, contact_sheet)],
        decisions=[],
        output_format="html",
    )

    assert report.format == "html"
    assert Path(report.artifact.path).suffix == ".html"
    assert "<script>" not in report.content
    assert "candidate-&lt;script&gt;" in report.content
    assert contact_sheet.resolve().as_uri() in report.content


def _score(candidate_run_id: str):
    return score_dataset_preview_candidates(
        [_comparison(candidate_run_id)],
        feedback_tags_by_candidate={},
        accepted_candidate_ids={candidate_run_id},
        quality_profile="balanced",
    )


def _comparison(candidate_run_id: str) -> PreviewRunComparison:
    return PreviewRunComparison(
        baseline=_manifest_summary("baseline"),
        candidate=_manifest_summary(candidate_run_id),
        pipeline_changed=True,
        inputs_changed=False,
        seed_changed=False,
        artifact_count_delta=0,
        review_notes=[],
        suggested_feedback_tags=[],
        quality_summary=PreviewQualitySummary(
            baseline=ImageQualityAggregate(image_count=1, brightness_mean=120.0),
            candidate=ImageQualityAggregate(image_count=1, brightness_mean=121.0),
        ),
    )


def _manifest_summary(run_id: str) -> PreviewManifestSummary:
    return PreviewManifestSummary(
        run_id=run_id,
        created_at="2026-06-13T12:00:00Z",
        input_count=1,
        transform_count=1,
        transform_names=["HorizontalFlip"],
    )


def _manifest(run_id: str, contact_sheet: Path) -> dict[str, object]:
    return {
        "run_id": run_id,
        "summary": {"contact_sheet_paths": [str(contact_sheet)]},
        "artifacts": [
            {
                "kind": "contact_sheet",
                "path": str(contact_sheet),
            },
        ],
    }


def _decision(decision_id: str, candidate_run_id: str) -> TuningDecisionRecord:
    summary = TuningSessionSummary(
        baseline_run_id="baseline",
        candidate_run_id=candidate_run_id,
        feedback_tags=[],
        accepted=True,
        export_ready=True,
        recommended_next_tool="export_pipeline",
        rationale="accepted",
        quality_score=100.0,
        quality_risk="low",
    )
    return TuningDecisionRecord(
        decision_id=decision_id,
        created_at="2026-06-13T12:01:00Z",
        baseline_run_id="baseline",
        candidate_run_id=candidate_run_id,
        accepted=True,
        export_ready=True,
        recommended_next_tool="export_pipeline",
        quality_score=100.0,
        quality_risk="low",
        reviewer_notes=["best sheet"],
        summary=summary,
    )
