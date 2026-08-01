from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from pydantic import ValidationError

from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.guided_preview import GuidedPreviewRequest, GuidedPreviewResult, GuidedPreviewService
from albumentationsx_mcp.models import (
    ArtifactKind,
    ArtifactRef,
    PreviewRequest,
    PreviewResult,
    RecipeRecommendation,
    TargetSpec,
)
from albumentationsx_mcp.onboarding import DatasetOnboardingReport, build_dataset_onboarding_report
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.preview import ArtifactStore, PathPolicy, PreviewService
from albumentationsx_mcp.preview_validation import PreviewRequestValidationReport, PreviewRequestValidator
from albumentationsx_mcp.recipes import recommend_recipe


class RecipeSpy:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> RecipeRecommendation:
        self.calls.append(kwargs)
        return recommend_recipe(**kwargs)


class RecordingValidator:
    def __init__(self, delegate: PreviewRequestValidator) -> None:
        self.delegate = delegate
        self.calls: list[tuple[dict[str, Any], TargetSpec]] = []

    def validate(
        self,
        request: dict[str, Any],
        *,
        target: TargetSpec | None = None,
    ) -> PreviewRequestValidationReport:
        assert target is not None
        self.calls.append((request, target))
        return self.delegate.validate(request, target=target)


class StubValidator:
    def __init__(self, report: PreviewRequestValidationReport | None = None) -> None:
        self.report = report
        self.calls: list[tuple[dict[str, Any], TargetSpec]] = []

    def validate(
        self,
        request: dict[str, Any],
        *,
        target: TargetSpec | None = None,
    ) -> PreviewRequestValidationReport:
        assert target is not None
        self.calls.append((request, target))
        if self.report is not None:
            return self.report
        return _validation_report(valid=True, normalized_request=request)


class RecordingRenderer:
    def __init__(self, delegate: PreviewService) -> None:
        self.delegate = delegate
        self.calls: list[PreviewRequest] = []

    def render_preview(self, request: PreviewRequest) -> PreviewResult:
        self.calls.append(request)
        return self.delegate.render_preview(request)


class StubRenderer:
    def __init__(
        self,
        result: PreviewResult | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[PreviewRequest] = []

    def render_preview(self, request: PreviewRequest) -> PreviewResult:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def test_guided_preview_renders_bounded_safe_template_with_traceable_contact_sheet(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset"
    for index in range(10):
        _write_image(dataset_path / f"{index:02d}.png", color=(index, 80, 160))

    path_policy = PathPolicy([dataset_path])
    pipeline_service = PipelineService(TransformCatalog())
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    validator = RecordingValidator(
        PreviewRequestValidator(pipeline_service=pipeline_service, path_policy=path_policy),
    )
    renderer = RecordingRenderer(PreviewService(pipeline_service, path_policy, artifact_store))
    recipe_builder = RecipeSpy()
    service = GuidedPreviewService(
        path_policy=path_policy,
        pipeline_service=pipeline_service,
        recipe_builder=recipe_builder,
        preview_validator=validator,
        preview_service=renderer,
    )

    result = service.run(GuidedPreviewRequest(dataset_path=dataset_path, max_images=8))

    assert result.status == "rendered"
    assert result.onboarding.preview_ready is True
    assert result.onboarding.image_count == 10
    assert result.onboarding.sampled_image_count == 8
    assert len(result.onboarding.sample_paths) <= 8
    template = result.onboarding.preview_request_template
    assert template is not None
    assert template.request["variants_per_image"] == 1
    assert template.request["seed"] == 0
    assert result.validation is not None
    assert result.validation.valid is True
    assert result.normalized_request is not None
    assert result.normalized_request["variants_per_image"] == 1
    assert result.normalized_request["seed"] == 0
    assert result.preview is not None
    contact_sheet = next(artifact for artifact in result.preview.artifacts if artifact.kind == "contact_sheet")
    assert result.contact_sheet is contact_sheet
    assert result.contact_sheet == contact_sheet
    assert result.trace_available is True
    assert "contact sheet" in result.next_actions[0].lower()
    assert "first variant trace" in result.next_actions[1].lower()
    assert "adjusting or rerendering" in result.next_actions[1].lower()

    manifest = artifact_store.read_manifest(result.preview.run_id)
    assert manifest["summary"]["variant_trace_count"] == result.onboarding.sampled_image_count
    assert len(manifest["variant_traces"]) == result.onboarding.sampled_image_count
    assert {(trace["image_index"], trace["variant_index"]) for trace in manifest["variant_traces"]} == {
        (index, 0) for index in range(8)
    }
    assert {trace["effective_seed"] for trace in manifest["variant_traces"]} == {0}

    assert recipe_builder.calls == [{"task": "classification", "intensity": "low", "targets": None}]
    assert len(validator.calls) == 1
    assert validator.calls[0][0] == template.request
    assert validator.calls[0][1] == TargetSpec(targets=result.onboarding.recipe.targets)
    assert len(renderer.calls) == 1
    assert renderer.calls[0].model_dump(mode="json", exclude_none=True) == result.normalized_request


def test_guided_preview_blocks_missing_dataset_before_validation_or_render(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    validator = StubValidator()
    renderer = StubRenderer()
    service = _service(path_policy=PathPolicy([tmp_path]), validator=validator, renderer=renderer)

    result = service.run(GuidedPreviewRequest(dataset_path=tmp_path / "missing"))

    _assert_onboarding_blocked(result, validator=validator, renderer=renderer)
    assert result.onboarding.checks[0].code == "dataset_path_missing"
    assert not artifact_root.exists()


def test_guided_preview_blocks_outside_allowed_root_before_validation_or_render(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    outside_path = _write_image(tmp_path / "outside" / "sample.png")
    artifact_root = tmp_path / "artifacts"
    validator = StubValidator()
    renderer = StubRenderer()
    service = _service(path_policy=PathPolicy([allowed_root]), validator=validator, renderer=renderer)

    result = service.run(GuidedPreviewRequest(dataset_path=outside_path))

    _assert_onboarding_blocked(result, validator=validator, renderer=renderer)
    assert result.onboarding.checks[0].code == "dataset_path_outside_allowed_root"
    assert not artifact_root.exists()


def test_guided_preview_blocks_empty_directory_before_validation_or_render(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset"
    dataset_path.mkdir()
    artifact_root = tmp_path / "artifacts"
    validator = StubValidator()
    renderer = StubRenderer()
    service = _service(path_policy=PathPolicy([tmp_path]), validator=validator, renderer=renderer)

    result = service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    _assert_onboarding_blocked(result, validator=validator, renderer=renderer)
    assert "dataset_images_missing" in {check.code for check in result.onboarding.checks}
    assert not artifact_root.exists()


def test_guided_preview_returns_injected_invalid_validation_report_without_rendering(tmp_path: Path) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    artifact_root = tmp_path / "artifacts"
    validation = _validation_report(
        valid=False,
        normalized_request=None,
        next_actions=["Fix the injected validation failure."],
    )
    validator = StubValidator(validation)
    renderer = StubRenderer()
    service = _service(path_policy=PathPolicy([tmp_path]), validator=validator, renderer=renderer)

    result = service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    _assert_validation_blocked(result, validation=validation, renderer=renderer)
    assert len(validator.calls) == 1
    assert result.next_actions == validation.next_actions
    assert not artifact_root.exists()


def test_guided_preview_blocks_valid_validation_without_normalized_request(tmp_path: Path) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    artifact_root = tmp_path / "artifacts"
    validation = _validation_report(
        valid=True,
        normalized_request=None,
        next_actions=["Validate the request again."],
    )
    validator = StubValidator(validation)
    renderer = StubRenderer()
    service = _service(path_policy=PathPolicy([tmp_path]), validator=validator, renderer=renderer)

    result = service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    _assert_validation_blocked(result, validation=validation, renderer=renderer)
    assert result.next_actions == validation.next_actions
    assert not artifact_root.exists()


def test_guided_preview_rejects_malformed_normalized_request_stably_before_render(tmp_path: Path) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    artifact_root = tmp_path / "artifacts"
    sensitive_value = "private-normalized-request-value"
    validation = _validation_report(
        valid=True,
        normalized_request={"unexpected": sensitive_value},
    )
    validator = StubValidator(validation)
    renderer = StubRenderer()
    service = _service(path_policy=PathPolicy([tmp_path]), validator=validator, renderer=renderer)

    with pytest.raises(ValueError, match=r"^Validated preview request is malformed$") as exc_info:
        service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    assert sensitive_value not in str(exc_info.value)
    assert renderer.calls == []
    assert not artifact_root.exists()


@pytest.mark.parametrize("contact_sheet_count", [0, 2])
def test_guided_preview_requires_exactly_one_rendered_contact_sheet(
    tmp_path: Path,
    contact_sheet_count: int,
) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    validator = StubValidator()
    contacts = [_artifact("contact_sheet", f"contact-{index}.png") for index in range(contact_sheet_count)]
    preview = PreviewResult(
        run_id="fake-run",
        artifacts=[_artifact("image", "image.png"), *contacts],
        manifest=_artifact("manifest", "manifest.json"),
        pipeline={},
    )
    renderer = StubRenderer(preview)
    service = _service(path_policy=PathPolicy([tmp_path]), validator=validator, renderer=renderer)

    with pytest.raises(
        ValueError,
        match=r"^Rendered preview must contain exactly one contact_sheet artifact$",
    ) as exc_info:
        service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    assert str(exc_info.value) == "Rendered preview must contain exactly one contact_sheet artifact"
    assert len(renderer.calls) == 1


def test_guided_preview_does_not_swallow_unexpected_preview_failure(tmp_path: Path) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    failure = RuntimeError("preview service failed")
    renderer = StubRenderer(error=failure)
    service = _service(path_policy=PathPolicy([tmp_path]), validator=StubValidator(), renderer=renderer)

    with pytest.raises(RuntimeError) as exc_info:
        service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    assert exc_info.value is failure


@pytest.mark.parametrize("max_images", [0, 9])
def test_guided_preview_request_rejects_max_image_bounds(tmp_path: Path, max_images: int) -> None:
    with pytest.raises(ValidationError):
        GuidedPreviewRequest.model_validate({"dataset_path": tmp_path, "max_images": max_images})


def test_guided_preview_request_uses_defaults_and_rejects_unknown_fields(tmp_path: Path) -> None:
    request = GuidedPreviewRequest(dataset_path=tmp_path)

    assert request.task == "classification"
    assert request.intensity == "low"
    assert request.targets is None
    assert request.max_images == 8
    with pytest.raises(ValidationError):
        GuidedPreviewRequest.model_validate({"dataset_path": tmp_path, "unknown": True})


def test_guided_preview_result_has_independent_defaults_and_rejects_unknown_fields(tmp_path: Path) -> None:
    onboarding = _blocked_onboarding(tmp_path)
    first = GuidedPreviewResult(status="blocked", onboarding=onboarding)
    second = GuidedPreviewResult(status="blocked", onboarding=onboarding)

    first.next_actions.append("inspect")

    assert second.next_actions == []
    assert first.validation is None
    assert first.normalized_request is None
    assert first.preview is None
    assert first.contact_sheet is None
    assert first.trace_available is False
    with pytest.raises(ValidationError):
        GuidedPreviewResult.model_validate(
            {
                "status": "blocked",
                "onboarding": onboarding,
                "unknown": True,
            }
        )


def _service(
    *,
    path_policy: PathPolicy,
    validator: StubValidator,
    renderer: StubRenderer,
) -> GuidedPreviewService:
    return GuidedPreviewService(
        path_policy=path_policy,
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
        preview_validator=validator,
        preview_service=renderer,
    )


def _validation_report(
    *,
    valid: bool,
    normalized_request: dict[str, Any] | None,
    next_actions: list[str] | None = None,
) -> PreviewRequestValidationReport:
    return PreviewRequestValidationReport(
        status="ok" if valid else "error",
        valid=valid,
        checks=[],
        warnings=[],
        next_actions=list(next_actions) if next_actions is not None else [],
        remediation_actions=[],
        normalized_request=normalized_request,
    )


def _assert_onboarding_blocked(
    result: GuidedPreviewResult,
    *,
    validator: StubValidator,
    renderer: StubRenderer,
) -> None:
    assert result.status == "blocked"
    assert result.onboarding.preview_ready is False
    assert result.validation is None
    assert result.normalized_request is None
    assert result.preview is None
    assert result.contact_sheet is None
    assert result.trace_available is False
    assert result.next_actions == result.onboarding.next_actions
    assert validator.calls == []
    assert renderer.calls == []


def _assert_validation_blocked(
    result: GuidedPreviewResult,
    *,
    validation: PreviewRequestValidationReport,
    renderer: StubRenderer,
) -> None:
    assert result.status == "blocked"
    assert result.onboarding.preview_ready is True
    assert result.validation is validation
    assert result.normalized_request is None
    assert result.preview is None
    assert result.contact_sheet is None
    assert result.trace_available is False
    assert result.next_actions == validation.next_actions
    assert renderer.calls == []


def _blocked_onboarding(tmp_path: Path) -> DatasetOnboardingReport:
    return build_dataset_onboarding_report(
        dataset_path=tmp_path / "missing",
        task="classification",
        intensity="low",
        targets=None,
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )


def _artifact(kind: ArtifactKind, filename: str) -> ArtifactRef:
    return ArtifactRef(
        kind=kind,
        uri=f"artifact://fake-run/{filename}",
        path=f"/artifacts/fake-run/{filename}",
        mime_type="application/json" if kind == "manifest" else "image/png",
        sha256="0" * 64,
        size_bytes=1,
    )


def _write_image(path: Path, *, color: tuple[int, int, int] = (80, 120, 160)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 12), color=color).save(path)
    return path
