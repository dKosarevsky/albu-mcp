"""Environment diagnostics for MCP hosts."""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from albumentationsx_mcp.models import StrictModel

DiagnosticStatus = Literal["ok", "warning", "error"]
WriteProbeStatus = Literal["not_run", "passed", "failed"]

_PROBE_FILENAME = ".albumentationsx-mcp-diagnostics-probe"
_REQUIRED_TOOLS = {
    "diagnose_environment",
    "recommend_recipe",
    "validate_pipeline",
    "render_preview_batch",
    "compare_preview_runs",
    "export_preview_report",
}
_REQUIRED_PROMPTS = {
    "build_robustness_augmentation_session",
    "compare_preview_runs_for_feedback",
}
_REQUIRED_WORKFLOW_RESOURCES = {
    "albumentationsx://diagnostics/guide",
    "albumentationsx://examples/client-smoke",
    "albumentationsx://recipes/catalog",
    "albumentationsx://workflows/preview-tuning",
}


class PublicSurface(StrictModel):
    """Public MCP surface advertised by the server."""

    tools: list[str]
    prompts: list[str]
    workflow_resources: list[str]


class DiagnosticCheck(StrictModel):
    """One machine-readable environment diagnostic check."""

    code: str
    status: DiagnosticStatus
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class DiagnosticsEnvironment(StrictModel):
    """Normalized environment details returned with diagnostics."""

    albumentationsx_version: str | None
    allowed_roots: list[str]
    artifact_root: str
    max_preview_runs: int
    write_probe: WriteProbeStatus


class DiagnosticsReport(StrictModel):
    """Agent-legible diagnostics report."""

    status: DiagnosticStatus
    checks: list[DiagnosticCheck]
    warnings: list[str]
    next_actions: list[str]
    environment: DiagnosticsEnvironment


class DiagnosticsGuideStep(StrictModel):
    """One step in the diagnostics host guide."""

    order: int
    tool: str
    instruction: str
    expected_result: str


class DiagnosticsGuide(StrictModel):
    """Machine-readable diagnostics playbook for MCP hosts."""

    name: str
    goal: str
    trigger_phrase: str
    steps: list[DiagnosticsGuideStep]
    success_criteria: list[str]
    failure_actions: list[str]


class DiagnosticsService:
    """Run bounded local checks that help MCP hosts diagnose setup issues."""

    def __init__(
        self,
        *,
        allowed_roots: list[Path],
        artifact_root: Path,
        max_preview_runs: int,
        public_surface: PublicSurface,
    ) -> None:
        self.allowed_roots = allowed_roots
        self.artifact_root = artifact_root
        self.max_preview_runs = max_preview_runs
        self.public_surface = public_surface

    def diagnose(self, *, include_write_probe: bool = True) -> DiagnosticsReport:
        """Return environment checks without reading user datasets."""
        checks: list[DiagnosticCheck] = []
        albumentationsx_version = self._check_albumentations_import(checks)
        checks.extend(self._allowed_root_checks())
        artifact_checks, write_probe = self._artifact_root_checks(include_write_probe=include_write_probe)
        checks.extend(artifact_checks)
        checks.extend(self._public_surface_checks())
        warnings = [check.message for check in checks if check.status == "warning"]
        return DiagnosticsReport(
            status=_aggregate_status(checks),
            checks=checks,
            warnings=warnings,
            next_actions=_next_actions(checks),
            environment=DiagnosticsEnvironment(
                albumentationsx_version=albumentationsx_version,
                allowed_roots=[str(path.expanduser().resolve()) for path in self.allowed_roots],
                artifact_root=str(self.artifact_root.expanduser().resolve()),
                max_preview_runs=self.max_preview_runs,
                write_probe=write_probe,
            ),
        )

    def _check_albumentations_import(self, checks: list[DiagnosticCheck]) -> str | None:
        try:
            module = import_module("albumentations")
            package_version = version("albumentationsx")
        except (ImportError, PackageNotFoundError) as exc:
            checks.append(
                DiagnosticCheck(
                    code="albumentationsx_import_failed",
                    status="error",
                    message="AlbumentationsX could not be imported by the MCP server.",
                    details={"error": str(exc)},
                )
            )
            return None
        module_version = str(getattr(module, "__version__", package_version))
        checks.append(
            DiagnosticCheck(
                code="albumentationsx_import",
                status="ok",
                message="AlbumentationsX is importable.",
                details={"module_version": module_version, "package_version": package_version},
            )
        )
        return package_version

    def _allowed_root_checks(self) -> list[DiagnosticCheck]:
        checks: list[DiagnosticCheck] = []
        for root in self.allowed_roots:
            resolved = root.expanduser().resolve()
            if not resolved.exists():
                checks.append(
                    DiagnosticCheck(
                        code="allowed_root_missing",
                        status="warning",
                        message=f"Allowed root does not exist: {resolved}",
                        details={"path": str(resolved)},
                    )
                )
            elif not resolved.is_dir():
                checks.append(
                    DiagnosticCheck(
                        code="allowed_root_not_directory",
                        status="error",
                        message=f"Allowed root is not a directory: {resolved}",
                        details={"path": str(resolved)},
                    )
                )
            else:
                checks.append(
                    DiagnosticCheck(
                        code="allowed_root_accessible",
                        status="ok",
                        message=f"Allowed root is accessible: {resolved}",
                        details={"path": str(resolved)},
                    )
                )
        return checks

    def _artifact_root_checks(self, *, include_write_probe: bool) -> tuple[list[DiagnosticCheck], WriteProbeStatus]:
        checks: list[DiagnosticCheck] = []
        resolved = self.artifact_root.expanduser().resolve()
        if resolved.exists() and not resolved.is_dir():
            checks.append(
                DiagnosticCheck(
                    code="artifact_root_not_directory",
                    status="error",
                    message=f"Artifact root is not a directory: {resolved}",
                    details={"path": str(resolved)},
                )
            )
            return checks, "failed" if include_write_probe else "not_run"
        try:
            resolved.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            checks.append(
                DiagnosticCheck(
                    code="artifact_root_unavailable",
                    status="error",
                    message=f"Artifact root could not be created: {resolved}",
                    details={"path": str(resolved), "error": str(exc)},
                )
            )
            return checks, "failed" if include_write_probe else "not_run"
        checks.append(
            DiagnosticCheck(
                code="artifact_root_accessible",
                status="ok",
                message=f"Artifact root is accessible: {resolved}",
                details={"path": str(resolved)},
            )
        )
        if not include_write_probe:
            return checks, "not_run"
        return self._write_probe(resolved, checks)

    @staticmethod
    def _write_probe(root: Path, checks: list[DiagnosticCheck]) -> tuple[list[DiagnosticCheck], WriteProbeStatus]:
        probe_path = root / _PROBE_FILENAME
        try:
            probe_path.write_text("ok\n", encoding="utf-8")
            probe_path.unlink(missing_ok=True)
        except OSError as exc:
            checks.append(
                DiagnosticCheck(
                    code="artifact_root_write_probe_failed",
                    status="error",
                    message="Artifact root write probe failed.",
                    details={"path": str(probe_path), "error": str(exc)},
                )
            )
            return checks, "failed"
        checks.append(
            DiagnosticCheck(
                code="artifact_root_write_probe",
                status="ok",
                message="Artifact root write probe passed.",
                details={"path": str(probe_path)},
            )
        )
        return checks, "passed"

    def _public_surface_checks(self) -> list[DiagnosticCheck]:
        return [
            _surface_check(
                code="required_tools_available",
                label="Required diagnostics tools",
                present=set(self.public_surface.tools),
                required=_REQUIRED_TOOLS,
            ),
            _surface_check(
                code="required_prompts_available",
                label="Required workflow prompts",
                present=set(self.public_surface.prompts),
                required=_REQUIRED_PROMPTS,
            ),
            _surface_check(
                code="required_workflow_resources_available",
                label="Required workflow resources",
                present=set(self.public_surface.workflow_resources),
                required=_REQUIRED_WORKFLOW_RESOURCES,
            ),
        ]


def build_diagnostics_guide() -> DiagnosticsGuide:
    """Return the canonical diagnostics playbook for MCP hosts."""
    return DiagnosticsGuide(
        name="diagnostics",
        goal="Diagnose AlbumentationsX MCP setup before rendering local previews.",
        trigger_phrase="why does AlbumentationsX MCP preview not work?",
        steps=[
            DiagnosticsGuideStep(
                order=1,
                tool="albumentationsx://diagnostics/guide",
                instruction="Read this guide so the host follows the supported diagnostics flow.",
                expected_result="A machine-readable playbook with checks, success criteria, and failure actions.",
            ),
            DiagnosticsGuideStep(
                order=2,
                tool="diagnose_environment",
                instruction="Call diagnose_environment with include_write_probe=true before preview rendering.",
                expected_result="A structured report with status, checks, warnings, environment, and next_actions.",
            ),
            DiagnosticsGuideStep(
                order=3,
                tool="albumentationsx://capabilities",
                instruction="Read capabilities to confirm tools, workflow resources, local roots, and preview limits.",
                expected_result="Configured roots, preview limits, tools, prompts, and workflow resources.",
            ),
        ],
        success_criteria=[
            "diagnose_environment returns status ok before rendering previews.",
            "Every warning or error is mapped to at least one concrete next action.",
            "The host confirms allowed_roots and artifact_root match the user's intended review folder.",
        ],
        failure_actions=[
            "If allowed_root_missing appears, restart the MCP host with a valid --allowed-root.",
            "If artifact_root_write_probe_failed appears, choose a writable --artifact-root outside the dataset.",
            "If required_tools_available fails, restart the host after upgrading albumentationsx-mcp.",
        ],
    )


def _surface_check(*, code: str, label: str, present: set[str], required: set[str]) -> DiagnosticCheck:
    missing = sorted(required - present)
    if missing:
        return DiagnosticCheck(
            code=code,
            status="error",
            message=f"{label} are missing from the advertised MCP surface.",
            details={"missing": missing},
        )
    return DiagnosticCheck(
        code=code,
        status="ok",
        message=f"{label} are available.",
        details={"required": sorted(required)},
    )


def _aggregate_status(checks: list[DiagnosticCheck]) -> DiagnosticStatus:
    statuses = {check.status for check in checks}
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "ok"


def _next_actions(checks: list[DiagnosticCheck]) -> list[str]:
    actions: list[str] = []
    codes = {check.code for check in checks if check.status != "ok"}
    if "albumentationsx_import_failed" in codes:
        actions.append("Reinstall the package with `uvx --from albumentationsx-mcp albumentationsx-mcp --help`.")
    if "allowed_root_missing" in codes or "allowed_root_not_directory" in codes:
        actions.append("Restart the MCP host with `--allowed-root /absolute/path/to/images`.")
    if "artifact_root_unavailable" in codes or "artifact_root_not_directory" in codes:
        actions.append("Restart the MCP host with `--artifact-root /absolute/path/to/writable-artifacts`.")
    if "artifact_root_write_probe_failed" in codes:
        actions.append("Choose a writable `--artifact-root` outside source datasets and restart the host.")
    if any(code.startswith("required_") for code in codes):
        actions.append("Restart the MCP host after upgrading to the latest `albumentationsx-mcp` package.")
    if not actions:
        actions.append("Proceed with `recommend_recipe`, `validate_pipeline`, and a small `render_preview_batch`.")
    return actions
