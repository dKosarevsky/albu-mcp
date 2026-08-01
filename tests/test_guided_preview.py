from __future__ import annotations

import json
from inspect import signature
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from pydantic import ValidationError

import albumentationsx_mcp.guided_preview as guided_preview_module
from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.guided_preview import GuidedPreviewRequest, GuidedPreviewResult, GuidedPreviewService
from albumentationsx_mcp.models import (
    MAX_SIGNED_64,
    ArtifactKind,
    ArtifactRef,
    PreviewRequest,
    PreviewResult,
    RecipeRecommendation,
    TargetSpec,
)
from albumentationsx_mcp.onboarding import DatasetOnboardingReport, RecipeBuilder, build_dataset_onboarding_report
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.presets import Intensity
from albumentationsx_mcp.preview import ArtifactStore, PathPolicy, PreviewService
from albumentationsx_mcp.preview_validation import PreviewRequestValidationReport, PreviewRequestValidator
from albumentationsx_mcp.recipes import recommend_recipe


class RecipeSpy:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> RecipeRecommendation:
        self.calls.append(kwargs)
        return recommend_recipe(**kwargs)


class StubOnboardingBuilder:
    def __init__(self, report: DatasetOnboardingReport) -> None:
        self.report = report
        self.calls: list[dict[str, Any]] = []

    def __call__(  # noqa: PLR0913
        self,
        *,
        dataset_path: Path,
        task: str,
        intensity: Intensity,
        targets: list[str] | None,
        path_policy: PathPolicy,
        pipeline_service: PipelineService,
        recipe_builder: RecipeBuilder,
        max_images: int = 8,
    ) -> DatasetOnboardingReport:
        self.calls.append(
            {
                "dataset_path": dataset_path,
                "task": task,
                "intensity": intensity,
                "targets": targets,
                "path_policy": path_policy,
                "pipeline_service": pipeline_service,
                "recipe_builder": recipe_builder,
                "max_images": max_images,
            }
        )
        return self.report


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


class EchoMutatingValidator:
    def __init__(self, *, valid: bool) -> None:
        self.valid = valid
        self.calls: list[tuple[dict[str, Any], TargetSpec]] = []
        self.report: PreviewRequestValidationReport | None = None

    def validate(
        self,
        request: dict[str, Any],
        *,
        target: TargetSpec | None = None,
    ) -> PreviewRequestValidationReport:
        assert target is not None
        self.calls.append((request, target))
        marker = request["pipeline"]["transforms"][0]["params"]["isolation"]
        assert isinstance(marker, dict)
        marker["owner"] = "validator"
        self.report = _validation_report(
            valid=self.valid,
            normalized_request=request,
            next_actions=["Fix the validator evidence."] if not self.valid else [],
        )
        return self.report


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


class MutatingRenderer(StubRenderer):
    def render_preview(self, request: PreviewRequest) -> PreviewResult:
        marker = request.pipeline.transforms[0].params["isolation"]
        assert isinstance(marker, dict)
        marker["owner"] = "renderer"
        return super().render_preview(request)


class RecordingArtifactStore(ArtifactStore):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.read_manifest_calls: list[str] = []

    def read_manifest(self, run_id: str) -> dict[str, Any]:
        self.read_manifest_calls.append(run_id)
        return super().read_manifest(run_id)


def test_guided_preview_injects_onboarding_builder_and_blocks_ready_report_without_template(tmp_path: Path) -> None:
    onboarding = _blocked_onboarding(tmp_path).model_copy(
        update={
            "status": "ok",
            "preview_ready": True,
            "preview_request_template": None,
            "next_actions": ["Supply a preview request template."],
        }
    )
    onboarding_builder = StubOnboardingBuilder(onboarding)
    path_policy = PathPolicy([tmp_path])
    pipeline_service = PipelineService(TransformCatalog())
    recipe_builder = RecipeSpy()
    validator = StubValidator()
    renderer = StubRenderer()
    service = GuidedPreviewService(
        path_policy=path_policy,
        pipeline_service=pipeline_service,
        recipe_builder=recipe_builder,
        preview_validator=validator,
        preview_service=renderer,
        onboarding_builder=onboarding_builder,
    )
    request = GuidedPreviewRequest(
        dataset_path=tmp_path / "virtual-dataset",
        task="segmentation",
        intensity="high",
        targets=["image", "mask"],
        max_images=3,
    )

    result = service.run(request)

    assert result.status == "blocked"
    assert result.onboarding is onboarding
    assert result.validation is None
    assert result.preview is None
    assert result.contact_sheet is None
    assert result.trace_available is False
    assert result.next_actions == onboarding.next_actions
    assert len(onboarding_builder.calls) == 1
    call = onboarding_builder.calls[0]
    assert call["dataset_path"] == request.dataset_path
    assert call["task"] == request.task
    assert call["intensity"] == request.intensity
    assert call["targets"] is request.targets
    assert call["max_images"] == request.max_images
    assert call["path_policy"] is path_policy
    assert call["pipeline_service"] is pipeline_service
    assert call["recipe_builder"] is recipe_builder
    assert recipe_builder.calls == []
    assert validator.calls == []
    assert renderer.calls == []


def test_guided_preview_service_uses_atomic_render_evidence_without_trace_lookup() -> None:
    assert "trace_lookup" not in signature(GuidedPreviewService).parameters


def test_guided_preview_exports_public_collaborator_protocols() -> None:
    assert guided_preview_module.PreviewValidator.__name__ == "PreviewValidator"
    assert guided_preview_module.PreviewRenderer.__name__ == "PreviewRenderer"
    assert guided_preview_module.OnboardingBuilder.__name__ == "OnboardingBuilder"


@pytest.mark.parametrize(("valid", "expected_status"), [(False, "blocked"), (True, "rendered")])
def test_guided_preview_detaches_validator_input_from_onboarding_template(
    tmp_path: Path,
    valid: object,
    expected_status: str,
) -> None:
    assert isinstance(valid, bool)
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    path_policy = PathPolicy([tmp_path])
    pipeline_service = PipelineService(TransformCatalog())
    onboarding = build_dataset_onboarding_report(
        dataset_path=dataset_path,
        task="classification",
        intensity="low",
        targets=None,
        path_policy=path_policy,
        pipeline_service=pipeline_service,
        recipe_builder=recommend_recipe,
        max_images=1,
    )
    template = onboarding.preview_request_template
    assert template is not None
    template_params = template.request["pipeline"]["transforms"][0]["params"]
    template_params["isolation"] = {"owner": "template"}
    original_onboarding_actions = list(onboarding.next_actions)
    validator = EchoMutatingValidator(valid=valid)
    renderer = StubRenderer(_preview_with_contact_sheet() if valid else None)
    service = GuidedPreviewService(
        path_policy=path_policy,
        pipeline_service=pipeline_service,
        recipe_builder=recommend_recipe,
        preview_validator=validator,
        preview_service=renderer,
        onboarding_builder=StubOnboardingBuilder(onboarding),
    )

    result = service.run(GuidedPreviewRequest(dataset_path=dataset_path, max_images=1))

    assert result.status == expected_status
    if valid:
        assert result.onboarding is not onboarding
        assert result.onboarding.next_actions == result.next_actions
        assert "validate_preview_request" not in " ".join(result.onboarding.next_actions)
        assert "render_preview_batch" not in " ".join(result.onboarding.next_actions)
    else:
        assert result.onboarding is onboarding
    assert validator.report is result.validation
    assert validator.calls[0][0] is not template.request
    assert template_params["isolation"] == {"owner": "template"}
    assert result.validation is not None
    assert result.validation.normalized_request is not None
    validation_params = result.validation.normalized_request["pipeline"]["transforms"][0]["params"]
    assert validation_params["isolation"] == {"owner": "validator"}
    assert result.normalized_request is not None
    result_params = result.normalized_request["pipeline"]["transforms"][0]["params"]
    assert result_params["isolation"] == {"owner": "validator"}

    validation_params["isolation"]["owner"] = "validation-caller"
    assert template_params["isolation"] == {"owner": "template"}
    assert result_params["isolation"] == {"owner": "validator"}
    template_params["isolation"]["owner"] = "template-caller"
    assert validation_params["isolation"] == {"owner": "validation-caller"}
    assert result_params["isolation"] == {"owner": "validator"}

    assert len(renderer.calls) == int(valid)
    assert result.trace_available is valid
    assert onboarding.next_actions == original_onboarding_actions
    if valid:
        result.onboarding.next_actions.append("caller mutation")
        assert result.next_actions[-1] != "caller mutation"
        assert onboarding.next_actions == original_onboarding_actions


def test_guided_preview_success_rewrites_all_nested_guidance_without_mutating_onboarding(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    _write_image(dataset_dir / "images" / "sample.png")
    annotations_dir = dataset_dir / "annotations"
    annotations_dir.mkdir()
    (annotations_dir / "instances.json").write_text(
        json.dumps(
            {
                "images": [{"id": 1, "file_name": "images/sample.png"}],
                "annotations": [{"id": 1, "image_id": 1, "bbox": [2, 3, 10, 8], "category_id": 7}],
                "categories": [{"id": 7, "name": "car"}],
            }
        ),
        encoding="utf-8",
    )
    path_policy = PathPolicy([tmp_path])
    pipeline_service = PipelineService(TransformCatalog())
    onboarding = build_dataset_onboarding_report(
        dataset_path=dataset_dir,
        task="object_detection",
        intensity="low",
        targets=["image", "bboxes"],
        path_policy=path_policy,
        pipeline_service=pipeline_service,
        recipe_builder=recommend_recipe,
        max_images=1,
    )
    source_template = onboarding.preview_request_template
    assert source_template is not None
    source_snapshot = onboarding.model_dump(mode="python")
    service = GuidedPreviewService(
        path_policy=path_policy,
        pipeline_service=pipeline_service,
        recipe_builder=recommend_recipe,
        preview_validator=StubValidator(),
        preview_service=StubRenderer(_preview_with_contact_sheet()),
        onboarding_builder=StubOnboardingBuilder(onboarding),
    )

    result = service.run(GuidedPreviewRequest(dataset_path=dataset_dir, targets=["image", "bboxes"], max_images=1))

    assert result.status == "rendered"
    completed_template = result.onboarding.preview_request_template
    assert completed_template is not None
    for guidance in (
        result.onboarding.next_actions,
        completed_template.instructions,
        result.onboarding.review_brief,
    ):
        normalized = " ".join(guidance).casefold()
        assert "validate_preview_request" not in normalized
        assert "render_preview_batch" not in normalized
        assert "validate preview_request_template.request before rendering" not in normalized
    assert all(
        anchor in " ".join(completed_template.instructions).casefold()
        for anchor in ("contact sheet", "trace_preview_variant", "adjust")
    )
    assert all(
        anchor in " ".join(result.onboarding.review_brief).casefold()
        for anchor in ("contact sheet", "trace_preview_variant", "adjust")
    )
    assert any("Annotation-aware template" in item for item in completed_template.instructions)
    assert any("overlay_contact_sheet" in item for item in completed_template.instructions)
    assert any("Bounding boxes require" in item for item in result.onboarding.review_brief)
    assert any("Annotation coverage" in item for item in result.onboarding.review_brief)
    assert completed_template.request == source_template.request
    assert completed_template.annotation_summary == source_template.annotation_summary
    assert onboarding.model_dump(mode="python") == source_snapshot
    assert "validate_preview_request" in " ".join(source_template.instructions)
    assert "Validate preview_request_template.request before rendering." in onboarding.review_brief


def test_guided_preview_renders_bounded_safe_template_with_traceable_contact_sheet(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset"
    for index in range(10):
        _write_image(dataset_path / f"{index:02d}.png", color=(index, 80, 160))

    path_policy = PathPolicy([dataset_path])
    pipeline_service = PipelineService(TransformCatalog())
    artifact_store = RecordingArtifactStore(tmp_path / "artifacts")
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
    assert result.preview.variant_trace_count == result.onboarding.sampled_image_count
    assert result.next_actions == [
        "Inspect the rendered contact sheet.",
        "Call `trace_preview_variant` for image_index=0 and variant_index=0.",
        "Use `adjust_pipeline` only after reviewing the contact sheet and first-variant trace evidence.",
    ]

    assert artifact_store.read_manifest_calls == []
    manifest = artifact_store.read_manifest(result.preview.run_id)
    assert manifest["summary"]["variant_trace_count"] == result.onboarding.sampled_image_count
    assert len(manifest["variant_traces"]) == result.onboarding.sampled_image_count
    assert {(trace["image_index"], trace["variant_index"]) for trace in manifest["variant_traces"]} == {
        (index, 0) for index in range(8)
    }
    assert {trace["effective_seed"] for trace in manifest["variant_traces"]} == {0}
    assert artifact_store.read_manifest_calls == [result.preview.run_id]

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
    service = _service(
        path_policy=PathPolicy([tmp_path]),
        validator=validator,
        renderer=renderer,
    )

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
    service = _service(
        path_policy=PathPolicy([allowed_root]),
        validator=validator,
        renderer=renderer,
    )

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
    service = _service(
        path_policy=PathPolicy([tmp_path]),
        validator=validator,
        renderer=renderer,
    )

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
    service = _service(
        path_policy=PathPolicy([tmp_path]),
        validator=validator,
        renderer=renderer,
    )

    result = service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    _assert_validation_blocked(result, validation=validation, renderer=renderer)
    assert len(validator.calls) == 1
    assert result.next_actions == validation.next_actions
    assert not artifact_root.exists()


def test_guided_preview_preserves_detached_invalid_normalized_request_without_rendering(tmp_path: Path) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    normalized_request = {"unexpected": {"owner": "validation"}}
    validation = _validation_report(
        valid=False,
        normalized_request=normalized_request,
        next_actions=["Fix the invalid normalized request."],
    )
    validator = StubValidator(validation)
    renderer = StubRenderer()
    service = _service(
        path_policy=PathPolicy([tmp_path]),
        validator=validator,
        renderer=renderer,
    )

    result = service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    assert result.status == "blocked"
    assert result.validation is validation
    assert result.normalized_request == validation.normalized_request
    assert result.normalized_request is not validation.normalized_request
    assert result.normalized_request is not None
    result.normalized_request["unexpected"]["owner"] = "caller"
    assert validation.normalized_request == {"unexpected": {"owner": "validation"}}
    assert normalized_request == {"unexpected": {"owner": "validation"}}
    assert result.preview is None
    assert result.contact_sheet is None
    assert result.trace_available is False
    assert result.next_actions == validation.next_actions
    assert renderer.calls == []


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
    service = _service(
        path_policy=PathPolicy([tmp_path]),
        validator=validator,
        renderer=renderer,
    )

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
    service = _service(
        path_policy=PathPolicy([tmp_path]),
        validator=validator,
        renderer=renderer,
    )

    with pytest.raises(ValueError, match=r"^Validated preview request is malformed$") as exc_info:
        service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    assert sensitive_value not in str(exc_info.value)
    assert renderer.calls == []
    assert not artifact_root.exists()


def test_guided_preview_rejects_validator_mutated_variants_before_render(tmp_path: Path) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    path_policy = PathPolicy([tmp_path])
    onboarding = _ready_onboarding(dataset_path, path_policy=path_policy, max_images=1)
    template = onboarding.preview_request_template
    assert template is not None
    validation = _validation_report(
        valid=True,
        normalized_request={**template.request, "variants_per_image": 2},
    )
    renderer = StubRenderer(_preview_with_contact_sheet(variant_trace_count=1))
    service = GuidedPreviewService(
        path_policy=path_policy,
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
        preview_validator=StubValidator(validation),
        preview_service=renderer,
        onboarding_builder=StubOnboardingBuilder(onboarding),
    )

    with pytest.raises(
        ValueError,
        match=r"^Validated preview request violates guided first-preview bounds$",
    ) as exc_info:
        service.run(GuidedPreviewRequest(dataset_path=dataset_path, max_images=1))

    assert type(exc_info.value) is ValueError
    assert str(exc_info.value) == "Validated preview request violates guided first-preview bounds"
    assert renderer.calls == []


@pytest.mark.parametrize("mutation", ["expansion", "substitution"])
def test_guided_preview_rejects_validator_mutated_input_paths_before_render(
    tmp_path: Path,
    mutation: str,
) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    path_policy = PathPolicy([tmp_path])
    onboarding = _ready_onboarding(dataset_path, path_policy=path_policy, max_images=1)
    replacement = _write_image(tmp_path / "private" / "replacement.png")
    template = onboarding.preview_request_template
    assert template is not None
    normalized_request = dict(template.request)
    normalized_request["input_paths"] = (
        [*template.request["input_paths"], str(replacement)] if mutation == "expansion" else [str(replacement)]
    )
    validation = _validation_report(valid=True, normalized_request=normalized_request)
    renderer = StubRenderer(_preview_with_contact_sheet(variant_trace_count=1))
    service = GuidedPreviewService(
        path_policy=path_policy,
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
        preview_validator=StubValidator(validation),
        preview_service=renderer,
        onboarding_builder=StubOnboardingBuilder(onboarding),
    )

    with pytest.raises(
        ValueError,
        match=r"^Validated preview request violates guided first-preview bounds$",
    ) as exc_info:
        service.run(GuidedPreviewRequest(dataset_path=dataset_path, max_images=2))

    assert str(replacement) not in str(exc_info.value)
    assert renderer.calls == []


def test_guided_preview_rejects_canonical_inputs_over_requested_max_without_rendering(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset"
    _write_image(dataset_path / "first.png")
    _write_image(dataset_path / "second.png")
    path_policy = PathPolicy([tmp_path])
    onboarding = _ready_onboarding(dataset_path, path_policy=path_policy, max_images=2)
    renderer = StubRenderer(_preview_with_contact_sheet(variant_trace_count=2))
    service = GuidedPreviewService(
        path_policy=path_policy,
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
        preview_validator=StubValidator(),
        preview_service=renderer,
        onboarding_builder=StubOnboardingBuilder(onboarding),
    )

    with pytest.raises(
        ValueError,
        match=r"^Validated preview request violates guided first-preview bounds$",
    ):
        service.run(GuidedPreviewRequest(dataset_path=dataset_path, max_images=1))

    assert onboarding.sampled_image_count == 2
    assert renderer.calls == []


def test_guided_preview_rejects_renderer_trace_undercount_for_canonical_request(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset"
    _write_image(dataset_path / "first.png")
    _write_image(dataset_path / "second.png")
    path_policy = PathPolicy([tmp_path])
    onboarding = _ready_onboarding(dataset_path, path_policy=path_policy, max_images=2)
    renderer = StubRenderer(_preview_with_contact_sheet(variant_trace_count=1))
    service = GuidedPreviewService(
        path_policy=path_policy,
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
        preview_validator=StubValidator(),
        preview_service=renderer,
        onboarding_builder=StubOnboardingBuilder(onboarding),
    )

    with pytest.raises(
        RuntimeError,
        match=r"^Rendered preview first variant trace is unavailable or inconsistent$",
    ):
        service.run(GuidedPreviewRequest(dataset_path=dataset_path, max_images=2))

    assert renderer.calls[0].input_paths == [Path(path) for path in onboarding.sample_paths]
    assert len(renderer.calls[0].input_paths) * renderer.calls[0].variants_per_image == 2


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
    service = _service(
        path_policy=PathPolicy([tmp_path]),
        validator=validator,
        renderer=renderer,
    )

    with pytest.raises(
        RuntimeError,
        match=r"^Rendered preview must contain exactly one contact_sheet artifact$",
    ) as exc_info:
        service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    assert type(exc_info.value) is RuntimeError
    assert str(exc_info.value) == "Rendered preview must contain exactly one contact_sheet artifact"
    assert len(renderer.calls) == 1


def test_guided_preview_accepts_consistent_atomic_trace_evidence(tmp_path: Path) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    renderer_preview = _preview_with_contact_sheet(variant_trace_count=0)
    renderer_preview.variant_trace_count = 1
    renderer = StubRenderer(renderer_preview)
    service = _service(
        path_policy=PathPolicy([tmp_path]),
        validator=StubValidator(),
        renderer=renderer,
    )

    result = service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    assert result.status == "rendered"
    assert result.trace_available is True
    assert result.preview is not None
    assert result.preview.variant_trace_count == 1
    assert result.preview is not renderer_preview


@pytest.mark.parametrize("variant_trace_count", [True, 1.0, "1", -1, MAX_SIGNED_64 + 1])
def test_guided_preview_revalidates_mutated_renderer_trace_count(
    tmp_path: Path,
    variant_trace_count: Any,
) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    renderer_preview = _preview_with_contact_sheet(variant_trace_count=1)
    renderer_preview.variant_trace_count = variant_trace_count
    renderer = StubRenderer(renderer_preview)
    service = _service(
        path_policy=PathPolicy([tmp_path]),
        validator=StubValidator(),
        renderer=renderer,
    )

    with pytest.raises(
        RuntimeError,
        match=r"^Rendered preview first variant trace is unavailable or inconsistent$",
    ) as exc_info:
        service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    assert type(exc_info.value) is RuntimeError
    assert str(exc_info.value) == "Rendered preview first variant trace is unavailable or inconsistent"


def test_guided_preview_revalidates_mutated_renderer_artifact_without_leaking_value(tmp_path: Path) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    renderer_preview = _preview_with_contact_sheet(variant_trace_count=1)
    sensitive_value = "private-invalid-artifact-kind"
    mutated_kind: Any = sensitive_value
    renderer_preview.artifacts[0].kind = mutated_kind
    renderer = StubRenderer(renderer_preview)
    service = _service(
        path_policy=PathPolicy([tmp_path]),
        validator=StubValidator(),
        renderer=renderer,
    )

    with pytest.raises(
        RuntimeError,
        match=r"^Rendered preview first variant trace is unavailable or inconsistent$",
    ) as exc_info:
        service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    assert type(exc_info.value) is RuntimeError
    assert str(exc_info.value) == "Rendered preview first variant trace is unavailable or inconsistent"
    assert sensitive_value not in str(exc_info.value)


def test_guided_preview_detaches_validation_render_and_result_object_graphs(tmp_path: Path) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    path_policy = PathPolicy([tmp_path])
    pipeline_service = PipelineService(TransformCatalog())
    onboarding = build_dataset_onboarding_report(
        dataset_path=dataset_path,
        task="classification",
        intensity="low",
        targets=None,
        path_policy=path_policy,
        pipeline_service=pipeline_service,
        recipe_builder=recommend_recipe,
        max_images=1,
    )
    template = onboarding.preview_request_template
    assert template is not None
    template_params = template.request["pipeline"]["transforms"][0]["params"]
    template_params["isolation"] = {"owner": "template"}
    validation = _validation_report(valid=True, normalized_request=template.request)
    renderer_preview = PreviewResult(
        run_id="renderer-owned-run",
        artifacts=[_artifact("image", "image.png"), _artifact("contact_sheet", "contact-sheet.png")],
        manifest=_artifact("manifest", "manifest.json"),
        pipeline={"nested": {"owner": "renderer-result"}},
        variant_trace_count=1,
    )
    renderer_contact = next(artifact for artifact in renderer_preview.artifacts if artifact.kind == "contact_sheet")
    renderer = MutatingRenderer(renderer_preview)
    service = GuidedPreviewService(
        path_policy=path_policy,
        pipeline_service=pipeline_service,
        recipe_builder=recommend_recipe,
        preview_validator=StubValidator(validation),
        preview_service=renderer,
        onboarding_builder=StubOnboardingBuilder(onboarding),
    )

    result = service.run(GuidedPreviewRequest(dataset_path=dataset_path, max_images=1))

    assert result.status == "rendered"
    assert result.normalized_request is not None
    assert result.normalized_request is not validation.normalized_request
    assert result.normalized_request["pipeline"]["transforms"][0]["params"]["isolation"] == {"owner": "template"}
    assert validation.normalized_request is not None
    assert validation.normalized_request["pipeline"]["transforms"][0]["params"]["isolation"] == {"owner": "template"}
    assert template.request["pipeline"]["transforms"][0]["params"]["isolation"] == {"owner": "template"}
    assert renderer.calls[0].pipeline.transforms[0].params["isolation"] == {"owner": "renderer"}
    assert result.preview is not None
    assert result.preview is not renderer_preview
    assert result.contact_sheet is next(
        artifact for artifact in result.preview.artifacts if artifact.kind == "contact_sheet"
    )
    assert result.contact_sheet is not renderer_contact

    result.normalized_request["pipeline"]["transforms"][0]["params"]["isolation"]["owner"] = "caller"
    result.preview.pipeline["nested"]["owner"] = "caller"
    assert result.contact_sheet is not None
    result.contact_sheet.path = "/caller/contact-sheet.png"

    assert validation.normalized_request["pipeline"]["transforms"][0]["params"]["isolation"] == {"owner": "template"}
    assert template.request["pipeline"]["transforms"][0]["params"]["isolation"] == {"owner": "template"}
    assert renderer_preview.pipeline == {"nested": {"owner": "renderer-result"}}
    assert renderer_contact.path == "/artifacts/fake-run/contact-sheet.png"


@pytest.mark.parametrize("variant_trace_count", [0, 2])
def test_guided_preview_rejects_missing_or_inconsistent_atomic_trace_evidence(
    tmp_path: Path,
    variant_trace_count: int,
) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    renderer = StubRenderer(_preview_with_contact_sheet(variant_trace_count=variant_trace_count))
    service = _service(
        path_policy=PathPolicy([tmp_path]),
        validator=StubValidator(),
        renderer=renderer,
    )

    with pytest.raises(
        RuntimeError,
        match=r"^Rendered preview first variant trace is unavailable or inconsistent$",
    ) as exc_info:
        service.run(GuidedPreviewRequest(dataset_path=dataset_path))

    assert type(exc_info.value) is RuntimeError
    assert str(exc_info.value) == "Rendered preview first variant trace is unavailable or inconsistent"


def test_guided_preview_does_not_swallow_unexpected_preview_failure(tmp_path: Path) -> None:
    dataset_path = _write_image(tmp_path / "dataset" / "sample.png")
    failure = RuntimeError("preview service failed")
    renderer = StubRenderer(error=failure)
    service = _service(
        path_policy=PathPolicy([tmp_path]),
        validator=StubValidator(),
        renderer=renderer,
    )

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


def _ready_onboarding(
    dataset_path: Path,
    *,
    path_policy: PathPolicy,
    max_images: int,
) -> DatasetOnboardingReport:
    return build_dataset_onboarding_report(
        dataset_path=dataset_path,
        task="classification",
        intensity="low",
        targets=None,
        path_policy=path_policy,
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
        max_images=max_images,
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


def _preview_with_contact_sheet(*, variant_trace_count: int = 1) -> PreviewResult:
    return PreviewResult(
        run_id="fake-run",
        artifacts=[_artifact("image", "image.png"), _artifact("contact_sheet", "contact-sheet.png")],
        manifest=_artifact("manifest", "manifest.json"),
        pipeline={},
        variant_trace_count=variant_trace_count,
    )


def _write_image(path: Path, *, color: tuple[int, int, int] = (80, 120, 160)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 12), color=color).save(path)
    return path
