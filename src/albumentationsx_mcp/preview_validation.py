"""Read-only preview request validation before rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

from pydantic import Field, ValidationError

from albumentationsx_mcp.diagnostics import DiagnosticSeverity, DiagnosticStatus
from albumentationsx_mcp.models import PreviewRequest, StrictModel, TargetSpec
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.preview import PathPolicy


class _PathCheckCodes(NamedTuple):
    accessible: str
    missing: str
    not_file: str
    outside: str


_INPUT_PATH_CODES = _PathCheckCodes(
    accessible="input_path_accessible",
    missing="input_path_missing",
    not_file="input_path_not_file",
    outside="input_path_outside_allowed_root",
)
_MASK_PATH_CODES = _PathCheckCodes(
    accessible="mask_path_accessible",
    missing="mask_path_missing",
    not_file="mask_path_not_file",
    outside="mask_path_outside_allowed_root",
)


class PreviewRequestCheck(StrictModel):
    """One machine-readable preview request validation check."""

    code: str
    status: DiagnosticStatus
    severity: DiagnosticSeverity = "info"
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class PreviewRequestRemediationAction(StrictModel):
    """One structured remediation action for a preview request validation report."""

    code: str
    severity: DiagnosticSeverity
    check_codes: list[str] = Field(default_factory=list)
    summary: str
    command_hint: str | None = None
    docs_uri: str | None = None


class PreviewRequestValidationReport(StrictModel):
    """Agent-legible preview request validation report."""

    status: DiagnosticStatus
    valid: bool
    checks: list[PreviewRequestCheck]
    warnings: list[str]
    next_actions: list[str]
    remediation_actions: list[PreviewRequestRemediationAction]
    normalized_request: dict[str, Any] | None = None


class PreviewRequestValidator:
    """Validate preview requests without rendering images or writing artifacts."""

    def __init__(self, *, pipeline_service: PipelineService, path_policy: PathPolicy) -> None:
        self.pipeline_service = pipeline_service
        self.path_policy = path_policy

    def validate(self, request: dict[str, Any], *, target: TargetSpec | None = None) -> PreviewRequestValidationReport:
        """Return structured validation results for a raw preview request payload."""
        checks: list[PreviewRequestCheck] = []
        target = target or TargetSpec()
        try:
            preview_request = PreviewRequest.model_validate(request)
        except ValidationError as exc:
            checks.append(
                PreviewRequestCheck(
                    code="preview_request_schema_invalid",
                    status="error",
                    severity="high",
                    message="Preview request schema is invalid.",
                    details={"errors": exc.errors(include_url=False)},
                )
            )
            return _report(checks, normalized_request=None)

        checks.append(
            PreviewRequestCheck(
                code="preview_request_schema_valid",
                status="ok",
                message="Preview request schema is valid.",
                details={
                    "input_count": len(preview_request.input_paths),
                    "variants_per_image": preview_request.variants_per_image,
                    "max_side": preview_request.max_side,
                },
            )
        )
        checks.extend(self._pipeline_checks(preview_request, target))
        checks.extend(self._input_path_checks(preview_request))
        checks.extend(self._annotation_checks(preview_request))
        return _report(checks, normalized_request=preview_request.model_dump(mode="json", exclude_none=True))

    def _pipeline_checks(self, request: PreviewRequest, target: TargetSpec) -> list[PreviewRequestCheck]:
        validation = self.pipeline_service.validate_pipeline(request.pipeline, target)
        if validation.valid:
            return [
                PreviewRequestCheck(
                    code="pipeline_valid",
                    status="ok",
                    message="Preview request pipeline is valid for the requested target.",
                    details={"warning_count": len(validation.warnings)},
                )
            ]
        return [
            PreviewRequestCheck(
                code="pipeline_invalid",
                status="error",
                severity="high",
                message="Preview request pipeline failed validation.",
                details={
                    "errors": [error.model_dump(mode="json") for error in validation.errors],
                    "warnings": [warning.model_dump(mode="json") for warning in validation.warnings],
                },
            )
        ]

    def _input_path_checks(self, request: PreviewRequest) -> list[PreviewRequestCheck]:
        return [
            self._path_check(
                path,
                codes=_INPUT_PATH_CODES,
                label=f"Input path {index + 1}",
            )
            for index, path in enumerate(request.input_paths)
        ]

    def _annotation_checks(self, request: PreviewRequest) -> list[PreviewRequestCheck]:
        checks: list[PreviewRequestCheck] = []
        if request.annotations is None:
            checks.append(
                PreviewRequestCheck(
                    code="annotation_count_matches",
                    status="ok",
                    message="No annotations were provided for this preview request.",
                    details={"input_count": len(request.input_paths), "annotation_count": 0},
                )
            )
            return checks
        if len(request.annotations) != len(request.input_paths):
            checks.append(
                PreviewRequestCheck(
                    code="annotation_count_mismatch",
                    status="error",
                    severity="high",
                    message="annotations length must match input_paths length.",
                    details={
                        "input_count": len(request.input_paths),
                        "annotation_count": len(request.annotations),
                    },
                )
            )
        else:
            checks.append(
                PreviewRequestCheck(
                    code="annotation_count_matches",
                    status="ok",
                    message="annotations length matches input_paths length.",
                    details={
                        "input_count": len(request.input_paths),
                        "annotation_count": len(request.annotations),
                    },
                )
            )
        for index, annotation in enumerate(request.annotations):
            if annotation is not None and annotation.mask_path is not None:
                checks.append(
                    self._path_check(
                        annotation.mask_path,
                        codes=_MASK_PATH_CODES,
                        label=f"Mask path {index + 1}",
                    )
                )
        return checks

    def _path_check(
        self,
        path: Path,
        *,
        codes: _PathCheckCodes,
        label: str,
    ) -> PreviewRequestCheck:
        resolved = path.expanduser().resolve()
        details = {"path": str(resolved), "allowed_roots": [str(root) for root in self.path_policy.allowed_roots]}
        if not self._is_allowed(resolved):
            return PreviewRequestCheck(
                code=codes.outside,
                status="error",
                severity="high",
                message=f"{label} is outside allowed roots: {resolved}",
                details=details,
            )
        if not resolved.exists():
            return PreviewRequestCheck(
                code=codes.missing,
                status="error",
                severity="high",
                message=f"{label} does not exist: {resolved}",
                details=details,
            )
        if not resolved.is_file():
            return PreviewRequestCheck(
                code=codes.not_file,
                status="error",
                severity="high",
                message=f"{label} is not a file: {resolved}",
                details=details,
            )
        return PreviewRequestCheck(
            code=codes.accessible,
            status="ok",
            message=f"{label} is accessible: {resolved}",
            details=details,
        )

    def _is_allowed(self, path: Path) -> bool:
        return any(path == root or root in path.parents for root in self.path_policy.allowed_roots)


def _report(
    checks: list[PreviewRequestCheck],
    *,
    normalized_request: dict[str, Any] | None,
) -> PreviewRequestValidationReport:
    status = _aggregate_status(checks)
    remediation_actions = _remediation_actions(checks)
    return PreviewRequestValidationReport(
        status=status,
        valid=status == "ok",
        checks=checks,
        warnings=[check.message for check in checks if check.status != "ok"],
        next_actions=_next_actions(status, checks),
        remediation_actions=remediation_actions,
        normalized_request=normalized_request,
    )


def _aggregate_status(checks: list[PreviewRequestCheck]) -> DiagnosticStatus:
    statuses = {check.status for check in checks}
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "ok"


def _remediation_actions(checks: list[PreviewRequestCheck]) -> list[PreviewRequestRemediationAction]:
    actions: list[PreviewRequestRemediationAction] = []
    codes = {check.code for check in checks if check.status != "ok"}
    if "preview_request_schema_invalid" in codes:
        actions.append(
            PreviewRequestRemediationAction(
                code="fix_preview_request_schema",
                severity="high",
                check_codes=["preview_request_schema_invalid"],
                summary="Fix the preview request payload before validating paths or rendering.",
            )
        )
    if "pipeline_invalid" in codes:
        actions.append(
            PreviewRequestRemediationAction(
                code="fix_pipeline",
                severity="high",
                check_codes=["pipeline_invalid"],
                summary="Call `validate_pipeline` and fix pipeline errors before rendering.",
            )
        )
    input_path_codes = [code for code in ("input_path_missing", "input_path_not_file") if code in codes]
    if input_path_codes:
        actions.append(
            PreviewRequestRemediationAction(
                code="fix_input_paths",
                severity="high",
                check_codes=input_path_codes,
                summary="Replace missing or non-file preview inputs with existing image files.",
            )
        )
    if "input_path_outside_allowed_root" in codes:
        actions.append(
            PreviewRequestRemediationAction(
                code="move_inputs_under_allowed_root",
                severity="high",
                check_codes=["input_path_outside_allowed_root"],
                summary="Move preview inputs under an allowed root or restart the server with a narrower correct root.",
                command_hint="--allowed-root /absolute/path/to/images",
            )
        )
    mask_path_codes = [
        code for code in ("mask_path_missing", "mask_path_not_file", "mask_path_outside_allowed_root") if code in codes
    ]
    if mask_path_codes:
        actions.append(
            PreviewRequestRemediationAction(
                code="fix_mask_paths",
                severity="high",
                check_codes=mask_path_codes,
                summary="Replace mask paths with existing mask image files under an allowed root.",
            )
        )
    if "annotation_count_mismatch" in codes:
        actions.append(
            PreviewRequestRemediationAction(
                code="fix_annotations",
                severity="high",
                check_codes=["annotation_count_mismatch"],
                summary="Provide exactly one annotation entry, or null, for each input path.",
            )
        )
    return actions


def _next_actions(status: DiagnosticStatus, checks: list[PreviewRequestCheck]) -> list[str]:
    if status == "ok":
        return ["Call `render_preview_batch` with the validated request."]
    return [check.message for check in checks if check.status != "ok"]
