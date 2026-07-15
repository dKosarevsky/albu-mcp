"""Read-only host smoke report assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from albumentationsx_mcp.diagnostics import (
    DiagnosticRemediationAction,
    DiagnosticSeverity,
    DiagnosticsReport,
    DiagnosticStatus,
)
from albumentationsx_mcp.models import PipelineValidationReport, RecipeRecommendation, StrictModel


class HostSmokeCheck(StrictModel):
    """One ordered check in a host smoke report."""

    code: str
    status: DiagnosticStatus
    severity: DiagnosticSeverity
    summary: str
    tool: str | None = None
    resource_uri: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class HostPreviewRequestTemplate(StrictModel):
    """Safe next preview request shape for MCP hosts."""

    tool: Literal["render_preview_batch"] = "render_preview_batch"
    request: dict[str, Any]
    instructions: list[str] = Field(default_factory=list)


class HostWorkflowExampleFallback(StrictModel):
    """Tool call for hosts that cannot expose MCP resource reads."""

    tool: Literal["get_workflow_example"] = "get_workflow_example"
    example_id: Literal["client-smoke"] = "client-smoke"


class HostWorkflowGuidance(StrictModel):
    """Host-neutral instructions that do not require model-visible MCP resources."""

    resource_uri: str = "albumentationsx://examples/client-smoke"
    resource_access: Literal["optional"] = "optional"
    fallback_tool: HostWorkflowExampleFallback | None = None
    instructions: list[str]


class HostSmokeReport(StrictModel):
    """Machine-readable host preflight report."""

    status: DiagnosticStatus
    preview_ready: bool
    workflow_guidance: HostWorkflowGuidance
    checks: list[HostSmokeCheck]
    diagnostics: DiagnosticsReport
    next_actions: list[str]
    remediation_actions: list[DiagnosticRemediationAction]
    preview_request_template: HostPreviewRequestTemplate | None = None


def build_host_smoke_report(
    *,
    diagnostics: DiagnosticsReport,
    recipe: RecipeRecommendation,
    validation: PipelineValidationReport,
) -> HostSmokeReport:
    """Build a read-only host smoke report from existing typed service outputs."""
    preview_ready = diagnostics.status == "ok" and validation.valid
    preview_request_template = _preview_request_template(diagnostics, recipe) if preview_ready else None
    checks = [
        _diagnostics_check(diagnostics),
        _recipe_check(recipe),
        _validation_check(validation),
        _preview_template_check(
            preview_ready=preview_ready,
            diagnostics=diagnostics,
            validation=validation,
        ),
    ]
    return HostSmokeReport(
        status=_aggregate_status(checks),
        preview_ready=preview_ready,
        workflow_guidance=_workflow_guidance(),
        checks=checks,
        diagnostics=diagnostics,
        next_actions=_next_actions(
            preview_ready=preview_ready,
            diagnostics=diagnostics,
            validation=validation,
        ),
        remediation_actions=diagnostics.remediation_actions,
        preview_request_template=preview_request_template,
    )


def _workflow_guidance() -> HostWorkflowGuidance:
    return HostWorkflowGuidance(
        fallback_tool=HostWorkflowExampleFallback(),
        instructions=[
            (
                "Read albumentationsx://examples/client-smoke when the host exposes resource reads; "
                "otherwise use this report directly."
            ),
            "Continue to preview validation and rendering only when preview_ready is true.",
            "Call validate_preview_request before render_preview_batch.",
            "Keep the first preview bounded to one small image and one variant.",
        ],
    )


def _diagnostics_check(diagnostics: DiagnosticsReport) -> HostSmokeCheck:
    return HostSmokeCheck(
        code="diagnostics",
        status=diagnostics.status,
        severity=_status_severity(diagnostics.status, diagnostics.remediation_actions),
        summary=f"diagnose_environment returned {diagnostics.status}.",
        tool="diagnose_environment",
        details={
            "check_count": len(diagnostics.checks),
            "warning_count": len(diagnostics.warnings),
            "write_probe": diagnostics.environment.write_probe,
        },
    )


def _recipe_check(recipe: RecipeRecommendation) -> HostSmokeCheck:
    return HostSmokeCheck(
        code="recipe_recommendation",
        status="ok",
        severity="info",
        summary=f"Selected {recipe.recipe_name} recipe with {recipe.quality_profile} quality profile.",
        tool="recommend_recipe",
        details={
            "task": recipe.task,
            "intensity": recipe.intensity,
            "targets": recipe.targets,
            "feedback_tags": recipe.feedback_tags,
        },
    )


def _validation_check(validation: PipelineValidationReport) -> HostSmokeCheck:
    status: DiagnosticStatus = "ok" if validation.valid else "error"
    return HostSmokeCheck(
        code="pipeline_validation",
        status=status,
        severity="info" if validation.valid else "high",
        summary="Recommended pipeline validated." if validation.valid else "Recommended pipeline failed validation.",
        tool="validate_pipeline",
        details={
            "valid": validation.valid,
            "error_count": len(validation.errors),
            "warning_count": len(validation.warnings),
            "errors": [error.model_dump(mode="json") for error in validation.errors],
            "warnings": [warning.model_dump(mode="json") for warning in validation.warnings],
        },
    )


def _preview_template_check(
    *,
    preview_ready: bool,
    diagnostics: DiagnosticsReport,
    validation: PipelineValidationReport,
) -> HostSmokeCheck:
    if preview_ready:
        return HostSmokeCheck(
            code="preview_request_template",
            status="ok",
            severity="info",
            summary="Preview request template is ready for render_preview_batch.",
            tool="render_preview_batch",
            details={"template_available": True},
        )
    if not validation.valid:
        return HostSmokeCheck(
            code="preview_request_template",
            status="error",
            severity="high",
            summary="Preview request template is blocked until the recommended pipeline validates.",
            tool="render_preview_batch",
            details={"template_available": False, "blocked_by": ["pipeline_validation"]},
        )
    return HostSmokeCheck(
        code="preview_request_template",
        status=diagnostics.status,
        severity=_status_severity(diagnostics.status, diagnostics.remediation_actions),
        summary="Preview request template is blocked until diagnostics warnings or errors are resolved.",
        tool="render_preview_batch",
        details={"template_available": False, "blocked_by": ["diagnostics"]},
    )


def _preview_request_template(
    diagnostics: DiagnosticsReport,
    recipe: RecipeRecommendation,
) -> HostPreviewRequestTemplate:
    allowed_root = Path(diagnostics.environment.allowed_roots[0])
    return HostPreviewRequestTemplate(
        request={
            "input_paths": [str(allowed_root / "example.jpg")],
            "pipeline": recipe.pipeline.model_dump(mode="json", exclude_none=True),
            "variants_per_image": 1,
            "seed": 0,
            "max_side": 512,
        },
        instructions=[
            "Replace the placeholder input path with one small image under an allowed root.",
            "Call `validate_preview_request` with this request before rendering.",
            "Keep variants_per_image at 1 until the first contact sheet is readable.",
            "Inspect the contact sheet before increasing intensity or rendering larger batches.",
        ],
    )


def _next_actions(
    *,
    preview_ready: bool,
    diagnostics: DiagnosticsReport,
    validation: PipelineValidationReport,
) -> list[str]:
    if preview_ready:
        return [
            "Replace the placeholder input path with one small image under an allowed root.",
            "Call `validate_preview_request` with `preview_request_template.request`.",
            "Call `render_preview_batch` with `preview_request_template.request`.",
            "Inspect the contact sheet before increasing variants, intensity, or batch size.",
        ]
    actions = list(diagnostics.next_actions)
    if not validation.valid:
        actions.append("Fix recommended pipeline validation errors before rendering previews.")
    if not actions:
        actions.append("Resolve host smoke warnings before rendering previews.")
    return actions


def _aggregate_status(checks: list[HostSmokeCheck]) -> DiagnosticStatus:
    statuses = {check.status for check in checks}
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "ok"


def _status_severity(
    status: DiagnosticStatus,
    remediation_actions: list[DiagnosticRemediationAction],
) -> DiagnosticSeverity:
    if status == "ok":
        return "info"
    severities = [action.severity for action in remediation_actions]
    if severities:
        return _max_severity(severities)
    return "medium" if status == "warning" else "high"


def _max_severity(severities: list[DiagnosticSeverity]) -> DiagnosticSeverity:
    rank: dict[DiagnosticSeverity, int] = {
        "info": 0,
        "medium": 1,
        "high": 2,
        "critical": 3,
    }
    return max(severities, key=lambda severity: rank[severity])
