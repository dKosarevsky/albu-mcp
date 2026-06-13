from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from albumentationsx_mcp.dataset import score_dataset_preview_candidates
from albumentationsx_mcp.models import (
    DatasetPreviewScore,
    ImageQualityAggregate,
    PreviewManifestSummary,
    PreviewQualitySummary,
    PreviewRunComparison,
    QualityFinding,
    TuningDecisionRecord,
    TuningSessionSummary,
)


@dataclass(frozen=True)
class PreviewReportCase:
    root: Path
    baseline_manifest: dict[str, object]
    candidate_manifests: list[dict[str, object]]
    score: DatasetPreviewScore
    decisions: list[TuningDecisionRecord]


def build_preview_report_case(root: Path) -> PreviewReportCase:
    image_root = root / "images"
    image_root.mkdir(parents=True, exist_ok=True)
    baseline_sheet = _write_png(image_root / "baseline-contact.png", (120, 120, 120))
    candidate_a_sheet = _write_png(image_root / "candidate-a-contact.png", (90, 150, 210))
    candidate_b_sheet = _write_png(image_root / "candidate-b-contact.png", (210, 90, 120))
    comparisons = [
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
    ]
    score = score_dataset_preview_candidates(
        comparisons,
        feedback_tags_by_candidate={"candidate-b": ["too_noisy:high"]},
        accepted_candidate_ids={"candidate-a"},
        quality_profile="classification",
    )
    return PreviewReportCase(
        root=root,
        baseline_manifest=_manifest("baseline", baseline_sheet),
        candidate_manifests=[
            _manifest("candidate-a", candidate_a_sheet),
            _manifest("candidate-b", candidate_b_sheet),
        ],
        score=score,
        decisions=[_decision("decision-a", "candidate-a")],
    )


def normalize_report_snapshot(content: str, root: Path) -> str:
    normalized = content.replace(str(root), "<FIXTURE_ROOT>")
    normalized = normalized.replace(root.resolve().as_uri(), "file://<FIXTURE_ROOT>")
    normalized = re.sub(
        r"artifact://reports/preview-report-baseline-[0-9a-f]{32}\.(md|html)",
        r"artifact://reports/preview-report-baseline.<\1>",
        normalized,
    )
    return re.sub(
        r"preview-report-baseline-[0-9a-f]{32}\.(md|html)",
        r"preview-report-baseline.<\1>",
        normalized,
    )


def _write_png(path: Path, color: tuple[int, int, int]) -> Path:
    Image.new("RGB", (8, 8), color).save(path)
    return path


def _comparison(candidate_run_id: str, *, brightness: float, clipping: float, findings: list[QualityFinding]):
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
        created_at="2026-06-13T12:00:00Z",
        input_count=2,
        variants_per_image=1,
        seed=137,
        transform_count=1,
        transform_names=["RandomBrightnessContrast"],
    )


def _manifest(run_id: str, contact_sheet: Path) -> dict[str, object]:
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


def _decision(decision_id: str, candidate_run_id: str) -> TuningDecisionRecord:
    summary = TuningSessionSummary(
        baseline_run_id="baseline",
        candidate_run_id=candidate_run_id,
        feedback_tags=["too_noisy:low"],
        accepted=True,
        export_ready=True,
        recommended_next_tool="export_pipeline",
        rationale="accepted",
        quality_score=100.0,
        quality_risk="low",
    )
    return TuningDecisionRecord(
        decision_id=decision_id,
        created_at="2026-06-13T12:05:00Z",
        baseline_run_id="baseline",
        candidate_run_id=candidate_run_id,
        feedback_tags=["too_noisy:low"],
        accepted=True,
        export_ready=True,
        recommended_next_tool="export_pipeline",
        quality_score=100.0,
        quality_risk="low",
        reviewer_notes=["accepted snapshot fixture"],
        summary=summary,
    )
