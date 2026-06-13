"""Preview report rendering and artifact export."""

from __future__ import annotations

import hashlib
import html
import re
import uuid
from pathlib import Path
from typing import Any, Literal

from albumentationsx_mcp.models import (
    ArtifactRef,
    DatasetFindingCount,
    DatasetMetricStats,
    DatasetPreviewScore,
    PreviewReportExport,
    TuningDecisionRecord,
)

ReportFormat = Literal["markdown", "html"]
_REPORT_MIME_TYPES: dict[ReportFormat, str] = {
    "markdown": "text/markdown",
    "html": "text/html",
}
_REPORT_SUFFIXES: dict[ReportFormat, str] = {
    "markdown": "md",
    "html": "html",
}
_SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_.-]+")


class PreviewReportService:
    """Render preview decision reports under a controlled artifact root."""

    def __init__(self, artifact_root: Path) -> None:
        self.artifact_root = artifact_root.resolve()
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.report_root = self.artifact_root / "reports"
        self.report_root.mkdir(parents=True, exist_ok=True)

    def export_report(
        self,
        score: DatasetPreviewScore,
        *,
        baseline_manifest: dict[str, Any],
        candidate_manifests: list[dict[str, Any]],
        decisions: list[TuningDecisionRecord],
        output_format: ReportFormat = "markdown",
    ) -> PreviewReportExport:
        """Render a Markdown or HTML preview report and return its artifact metadata."""
        if output_format not in _REPORT_MIME_TYPES:
            msg = f"Unsupported preview report format: {output_format}"
            raise ValueError(msg)

        content = (
            _render_markdown_report(score, baseline_manifest, candidate_manifests, decisions)
            if output_format == "markdown"
            else _render_html_report(score, baseline_manifest, candidate_manifests, decisions)
        )
        path = self._report_path(score.baseline_run_id, output_format)
        path.write_text(content, encoding="utf-8")
        return PreviewReportExport(
            format=output_format,
            content=content,
            artifact=self._artifact_ref(path, mime_type=_REPORT_MIME_TYPES[output_format]),
            baseline_run_id=score.baseline_run_id,
            candidate_count=score.candidate_count,
            best_candidate_run_id=score.best_candidate_run_id,
        )

    def _report_path(self, baseline_run_id: str, output_format: ReportFormat) -> Path:
        safe_baseline = _safe_name(baseline_run_id or "dataset")
        suffix = _REPORT_SUFFIXES[output_format]
        return self.report_root / f"preview-report-{safe_baseline}-{uuid.uuid4().hex}.{suffix}"

    def _artifact_ref(self, path: Path, *, mime_type: str) -> ArtifactRef:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return ArtifactRef(
            kind="report",
            uri=f"artifact://{path.relative_to(self.artifact_root)}",
            path=str(path),
            mime_type=mime_type,
            sha256=digest,
            size_bytes=path.stat().st_size,
        )


def _render_markdown_report(
    score: DatasetPreviewScore,
    baseline_manifest: dict[str, Any],
    candidate_manifests: list[dict[str, Any]],
    decisions: list[TuningDecisionRecord],
) -> str:
    candidate_contact_sheets = _contact_sheets_by_run_id(candidate_manifests)
    lines = [
        "# AlbumentationsX MCP Preview Report",
        "",
        f"- Baseline run: {score.baseline_run_id}",
        f"- Quality profile: {score.quality_profile}",
        f"- Candidates: {score.candidate_count}",
        f"- Best candidate: {score.best_candidate_run_id or 'none'}",
        "",
        "## Contact Sheets",
        "",
        "### Baseline",
        "",
        *_markdown_paths(_contact_sheet_paths(baseline_manifest)),
        "",
        "### Candidates",
        "",
        "| Rank | Candidate | Score | Risk | Export Ready | Next Tool | Feedback Tags | Contact Sheets |",
        "| ---: | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        (
            "| "
            f"{candidate.rank} | "
            f"{candidate.candidate_run_id} | "
            f"{candidate.quality_score:.1f} | "
            f"{candidate.quality_risk} | "
            f"{str(candidate.export_ready).lower()} | "
            f"{candidate.recommended_next_tool} | "
            f"{', '.join(candidate.feedback_tags) or 'none'} | "
            f"{_markdown_contact_sheet_cell(candidate_contact_sheets.get(candidate.candidate_run_id, []))} |"
        )
        for candidate in score.ranking.ranked_candidates
    )
    lines.extend(
        [
            "",
            "## Dataset Metrics",
            "",
            *_markdown_metric_stats(score.metric_stats),
            "",
            "## Finding Counts",
            "",
            *_markdown_finding_counts(score.finding_counts),
            "",
            "## Tuning Decisions",
            "",
            *_markdown_decisions(decisions),
            "",
        ],
    )
    return "\n".join(lines)


def _render_html_report(
    score: DatasetPreviewScore,
    baseline_manifest: dict[str, Any],
    candidate_manifests: list[dict[str, Any]],
    decisions: list[TuningDecisionRecord],
) -> str:
    candidate_contact_sheets = _contact_sheets_by_run_id(candidate_manifests)
    rows = []
    for candidate in score.ranking.ranked_candidates:
        contact_links = _html_contact_sheet_links(candidate_contact_sheets.get(candidate.candidate_run_id, []))
        rows.append(
            "<tr>"
            f"<td>{candidate.rank}</td>"
            f"<td>{html.escape(candidate.candidate_run_id)}</td>"
            f"<td>{candidate.quality_score:.1f}</td>"
            f"<td>{html.escape(candidate.quality_risk)}</td>"
            f"<td>{str(candidate.export_ready).lower()}</td>"
            f"<td>{html.escape(candidate.recommended_next_tool)}</td>"
            f"<td>{html.escape(', '.join(candidate.feedback_tags) or 'none')}</td>"
            f"<td>{contact_links or 'none'}</td>"
            "</tr>",
        )
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            "<title>AlbumentationsX MCP Preview Report</title>",
            "<style>body{font-family:system-ui,sans-serif;line-height:1.45;margin:2rem}"
            "table{border-collapse:collapse;width:100%;margin:1rem 0}"
            "td,th{border:1px solid #ddd;padding:.4rem;text-align:left}"
            "th{background:#f6f8fa}"
            ".contact-sheet{max-width:240px;height:auto;display:block;margin:.25rem 0}</style>",
            "</head>",
            "<body>",
            "<h1>AlbumentationsX MCP Preview Report</h1>",
            "<ul>",
            f"<li>Baseline run: {html.escape(score.baseline_run_id)}</li>",
            f"<li>Quality profile: {html.escape(score.quality_profile)}</li>",
            f"<li>Candidates: {score.candidate_count}</li>",
            f"<li>Best candidate: {html.escape(score.best_candidate_run_id or 'none')}</li>",
            "</ul>",
            "<h2>Baseline Contact Sheets</h2>",
            _html_path_list(_contact_sheet_paths(baseline_manifest)),
            "<h2>Candidates</h2>",
            "<table><thead><tr>"
            "<th>Rank</th><th>Candidate</th><th>Score</th><th>Risk</th>"
            "<th>Export Ready</th><th>Next Tool</th><th>Feedback Tags</th><th>Contact Sheets</th>"
            "</tr></thead><tbody>",
            *rows,
            "</tbody></table>",
            "<h2>Dataset Metrics</h2>",
            _html_metric_stats(score.metric_stats),
            "<h2>Finding Counts</h2>",
            _html_finding_counts(score.finding_counts),
            "<h2>Tuning Decisions</h2>",
            _html_decisions(decisions),
            "</body></html>",
        ],
    )


def _contact_sheets_by_run_id(manifests: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {str(manifest.get("run_id", "")): _contact_sheet_paths(manifest) for manifest in manifests}


def _contact_sheet_paths(manifest: dict[str, Any]) -> list[str]:
    summary = manifest.get("summary")
    if isinstance(summary, dict) and isinstance(summary.get("contact_sheet_paths"), list):
        return [str(path) for path in summary["contact_sheet_paths"]]
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return []
    return [
        str(artifact["path"])
        for artifact in artifacts
        if isinstance(artifact, dict)
        and artifact.get("kind") in {"contact_sheet", "overlay_contact_sheet"}
        and "path" in artifact
    ]


def _markdown_paths(paths: list[str]) -> list[str]:
    if not paths:
        return ["- none"]
    lines: list[str] = []
    for path in paths:
        lines.append(f"- ![contact sheet]({path})")
        lines.append(f"- {path}")
    return lines


def _markdown_contact_sheet_cell(paths: list[str]) -> str:
    if not paths:
        return "none"
    return "<br>".join(f"![contact sheet]({path})<br>{path}" for path in paths)


def _markdown_metric_stats(stats: list[DatasetMetricStats]) -> list[str]:
    if not stats:
        return ["No dataset metric stats available."]
    lines = [
        "| Metric | Candidates | Min | Max | Mean |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(
        (
            f"| {item.metric} | {item.candidate_count} | "
            f"{item.min_value:.4f} | {item.max_value:.4f} | {item.mean_value:.4f} |"
        )
        for item in stats
    )
    return lines


def _markdown_finding_counts(counts: list[DatasetFindingCount]) -> list[str]:
    if not counts:
        return ["No quality findings across candidates."]
    lines = [
        "| Severity | Code | Count |",
        "| --- | --- | ---: |",
    ]
    lines.extend(f"| {item.severity} | {item.code} | {item.count} |" for item in counts)
    return lines


def _markdown_decisions(decisions: list[TuningDecisionRecord]) -> list[str]:
    if not decisions:
        return ["No persisted decisions matched this report."]
    lines = [
        "| Decision | Candidate | Accepted | Score | Risk | Notes |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    lines.extend(
        (
            "| "
            f"{decision.decision_id} | "
            f"{decision.candidate_run_id} | "
            f"{str(decision.accepted).lower()} | "
            f"{decision.quality_score:.1f} | "
            f"{decision.quality_risk} | "
            f"{'; '.join(decision.reviewer_notes)} |"
        )
        for decision in decisions
    )
    return lines


def _html_path_list(paths: list[str]) -> str:
    if not paths:
        return "<p>none</p>"
    items = [f"<li>{_html_contact_sheet_link(path)}</li>" for path in paths]
    return f"<ul>{''.join(items)}</ul>"


def _html_contact_sheet_links(paths: list[str]) -> str:
    if not paths:
        return "none"
    return "".join(f"{_html_contact_sheet_link(path)}<br>" for path in paths)


def _html_contact_sheet_link(path: str) -> str:
    uri = html.escape(_file_uri(path), quote=True)
    escaped_path = html.escape(path)
    return f'<a href="{uri}"><img class="contact-sheet" src="{uri}" alt="contact sheet"></a><span>{escaped_path}</span>'


def _html_metric_stats(stats: list[DatasetMetricStats]) -> str:
    if not stats:
        return "<p>No dataset metric stats available.</p>"
    rows = [
        "<tr>"
        f"<td>{html.escape(item.metric)}</td>"
        f"<td>{item.candidate_count}</td>"
        f"<td>{item.min_value:.4f}</td>"
        f"<td>{item.max_value:.4f}</td>"
        f"<td>{item.mean_value:.4f}</td>"
        "</tr>"
        for item in stats
    ]
    return (
        "<table><thead><tr><th>Metric</th><th>Candidates</th><th>Min</th><th>Max</th><th>Mean</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def _html_finding_counts(counts: list[DatasetFindingCount]) -> str:
    if not counts:
        return "<p>No quality findings across candidates.</p>"
    rows = [
        f"<tr><td>{html.escape(item.severity)}</td><td>{html.escape(item.code)}</td><td>{item.count}</td></tr>"
        for item in counts
    ]
    return (
        "<table><thead><tr><th>Severity</th><th>Code</th><th>Count</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _html_decisions(decisions: list[TuningDecisionRecord]) -> str:
    if not decisions:
        return "<p>No persisted decisions matched this report.</p>"
    rows = [
        "<tr>"
        f"<td>{html.escape(decision.decision_id)}</td>"
        f"<td>{html.escape(decision.candidate_run_id)}</td>"
        f"<td>{str(decision.accepted).lower()}</td>"
        f"<td>{decision.quality_score:.1f}</td>"
        f"<td>{html.escape(decision.quality_risk)}</td>"
        f"<td>{html.escape('; '.join(decision.reviewer_notes))}</td>"
        "</tr>"
        for decision in decisions
    ]
    return (
        "<table><thead><tr><th>Decision</th><th>Candidate</th><th>Accepted</th>"
        f"<th>Score</th><th>Risk</th><th>Notes</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def _file_uri(path: str) -> str:
    return Path(path).expanduser().resolve().as_uri()


def _safe_name(value: str) -> str:
    safe = _SAFE_NAME_PATTERN.sub("-", value).strip("-")
    return safe or "preview"
