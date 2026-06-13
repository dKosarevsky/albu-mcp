from pathlib import Path

import pytest

from albumentationsx_mcp.reports import PreviewReportService, ReportFormat
from tests.fixtures.report_case import build_preview_report_case, normalize_report_snapshot


@pytest.mark.parametrize(
    ("output_format", "snapshot_name"),
    [
        ("markdown", "preview_report.md"),
        ("html", "preview_report.html"),
    ],
)
def test_preview_report_snapshots_include_real_contact_sheet_images(
    tmp_path: Path,
    output_format: ReportFormat,
    snapshot_name: str,
) -> None:
    report_case = build_preview_report_case(tmp_path)

    report = PreviewReportService(tmp_path / "artifacts").export_report(
        report_case.score,
        baseline_manifest=report_case.baseline_manifest,
        candidate_manifests=report_case.candidate_manifests,
        decisions=report_case.decisions,
        output_format=output_format,
    )

    assert Path(report.artifact.path).exists()
    normalized = normalize_report_snapshot(report.content, tmp_path)
    expected = (Path("tests/fixtures/snapshots") / snapshot_name).read_text(encoding="utf-8")
    assert normalized.rstrip() == expected.rstrip()
