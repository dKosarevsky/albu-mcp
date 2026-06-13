"""Preview rendering with scoped filesystem access."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from PIL import Image

from albumentationsx_mcp.annotations import (
    annotation_has_content,
    build_transform_payload,
    load_mask,
    render_overlay,
    scale_annotations,
)
from albumentationsx_mcp.models import (
    AnnotationObservation,
    ArtifactKind,
    ArtifactRef,
    ComposeSpec,
    PreviewRequest,
    PreviewResult,
    PreviewRunComparison,
    PreviewRunSummary,
)
from albumentationsx_mcp.preview_analysis import compare_preview_manifests
from albumentationsx_mcp.quality import compare_manifest_quality

_RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class PipelineBuilder(Protocol):
    """Builds executable Albumentations pipelines from validated specs."""

    def build_pipeline(self, pipeline: ComposeSpec) -> Any: ...


class PathPolicy:
    """Allowlist-based path resolver for local image access."""

    def __init__(self, allowed_roots: list[Path]) -> None:
        if not allowed_roots:
            msg = "At least one allowed root is required"
            raise ValueError(msg)
        self.allowed_roots = [root.resolve() for root in allowed_roots]

    def resolve_input(self, path: Path) -> Path:
        """Resolve an existing input path and ensure it is inside an allowed root."""
        resolved = path.expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(resolved)
        if not self._is_allowed(resolved):
            msg = f"Input path is outside allowed roots: {resolved}"
            raise ValueError(msg)
        return resolved

    def _is_allowed(self, path: Path) -> bool:
        return any(path == root or root in path.parents for root in self.allowed_roots)


class ArtifactStore:
    """Writes preview artifacts under one controlled root directory."""

    def __init__(self, root: Path, *, max_runs: int = 100) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self.max_runs = max(1, max_runs)

    def create_run_dir(self) -> tuple[str, Path]:
        run_id = uuid.uuid4().hex
        run_dir = self.root / run_id
        run_dir.mkdir(parents=True)
        return run_id, run_dir

    def artifact_ref(self, path: Path, *, kind: ArtifactKind, mime_type: str) -> ArtifactRef:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return ArtifactRef(
            kind=kind,
            uri=f"artifact://{path.relative_to(self.root)}",
            path=str(path),
            mime_type=mime_type,
            sha256=digest,
            size_bytes=path.stat().st_size,
        )

    def record_run(self, manifest_data: dict[str, Any]) -> None:
        """Record a preview run in a queryable local index."""
        run_id = str(manifest_data["run_id"])
        artifacts = list(manifest_data.get("artifacts", []))
        contact_sheet = next((artifact for artifact in artifacts if artifact.get("kind") == "contact_sheet"), None)
        summary = PreviewRunSummary(
            run_id=run_id,
            created_at=str(manifest_data["created_at"]),
            manifest_path=str(self.root / run_id / "manifest.json"),
            artifact_count=len(artifacts),
            input_count=len(manifest_data.get("inputs", [])),
            contact_sheet_path=contact_sheet.get("path") if contact_sheet else None,
        )
        existing = [run for run in self._read_index() if run.run_id != run_id]
        runs = [summary, *existing]
        self._write_index(runs[: self.max_runs])
        for stale_run in runs[self.max_runs :]:
            self._delete_run_dir(stale_run.run_id)

    def list_runs(self, limit: int = 20) -> list[PreviewRunSummary]:
        """Return recent preview run summaries, newest first."""
        return self._read_index()[: max(0, limit)]

    def read_manifest(self, run_id: str) -> dict[str, Any]:
        """Read a preview manifest by run id without allowing path traversal."""
        manifest_path = self._run_dir(run_id) / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(manifest_path)
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def delete_run(self, run_id: str) -> PreviewRunSummary:
        """Delete a preview run directory and remove it from the local index."""
        run_dir = self._run_dir(run_id)
        runs = self._read_index()
        summary = next((run for run in runs if run.run_id == run_id), None)
        if summary is None:
            raise FileNotFoundError(run_dir)
        self._delete_run_dir(run_id)
        self._write_index([run for run in runs if run.run_id != run_id])
        return summary

    def cleanup_runs(self, keep_last: int | None = None) -> list[PreviewRunSummary]:
        """Delete older preview runs beyond the requested retention count."""
        keep_count = self.max_runs if keep_last is None else max(0, keep_last)
        runs = self._read_index()
        retained = runs[:keep_count]
        deleted = runs[keep_count:]
        for run in deleted:
            self._delete_run_dir(run.run_id)
        self._write_index(retained)
        return deleted

    def _read_index(self) -> list[PreviewRunSummary]:
        if not self.index_path.exists():
            return []
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        return [PreviewRunSummary.model_validate(item) for item in payload.get("runs", [])]

    def _write_index(self, runs: list[PreviewRunSummary]) -> None:
        payload = {"runs": [run.model_dump(mode="json") for run in runs]}
        self.index_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _run_dir(self, run_id: str) -> Path:
        if not _RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError(f"Invalid preview run id: {run_id}")
        return self.root / run_id

    def _delete_run_dir(self, run_id: str) -> None:
        shutil.rmtree(self._run_dir(run_id), ignore_errors=True)


class PreviewService:
    """Render deterministic preview images for a pipeline spec."""

    def __init__(
        self,
        pipeline_service: PipelineBuilder,
        path_policy: PathPolicy,
        artifact_store: ArtifactStore,
    ) -> None:
        self.pipeline_service = pipeline_service
        self.path_policy = path_policy
        self.artifact_store = artifact_store

    def render_preview(self, request: PreviewRequest) -> PreviewResult:
        """Apply the pipeline to local images and write preview artifacts."""
        run_id, run_dir = self.artifact_store.create_run_dir()
        artifacts: list[ArtifactRef] = []
        image_paths: list[Path] = []
        overlay_paths: list[Path] = []
        annotation_observations: list[AnnotationObservation] = []
        source_paths = [self.path_policy.resolve_input(path) for path in request.input_paths]
        annotations = self._resolve_annotations(request)

        for source_index, source_path in enumerate(source_paths):
            image, original_size = self._load_rgb(source_path, request.max_side)
            annotation = scale_annotations(
                annotations[source_index],
                original_size=original_size,
                output_size=image.size,
            )
            if annotation and annotation.mask_path is not None:
                annotation.mask_path = self.path_policy.resolve_input(annotation.mask_path)
            mask = load_mask(annotation.mask_path if annotation else None, image.size)
            for variant_index in range(request.variants_per_image):
                pipeline = request.pipeline.model_copy(deep=True)
                if request.seed is not None:
                    pipeline.seed = request.seed + variant_index
                transform = self.pipeline_service.build_pipeline(pipeline)
                result = transform(**build_transform_payload(image, annotation, mask))
                if annotation_has_content(annotation):
                    annotation_observations.append(
                        self._annotation_observation(
                            image_index=source_index,
                            variant_index=variant_index,
                            annotation=annotation,
                            input_mask=mask,
                            result=result,
                        ),
                    )
                output = run_dir / f"{source_index:03d}-{variant_index:03d}.png"
                Image.fromarray(result["image"]).save(output)
                image_paths.append(output)
                artifacts.append(self.artifact_store.artifact_ref(output, kind="image", mime_type="image/png"))
                if annotation_has_content(annotation):
                    overlay_output = run_dir / f"{source_index:03d}-{variant_index:03d}-overlay.png"
                    render_overlay(result).save(overlay_output)
                    overlay_paths.append(overlay_output)
                    artifacts.append(
                        self.artifact_store.artifact_ref(overlay_output, kind="overlay", mime_type="image/png"),
                    )

        contact_sheet_path = run_dir / "contact_sheet.png"
        self._write_contact_sheet(image_paths, contact_sheet_path)
        artifacts.append(
            self.artifact_store.artifact_ref(
                contact_sheet_path,
                kind="contact_sheet",
                mime_type="image/png",
            ),
        )
        if overlay_paths:
            overlay_contact_sheet_path = run_dir / "overlay_contact_sheet.png"
            self._write_contact_sheet(overlay_paths, overlay_contact_sheet_path)
            artifacts.append(
                self.artifact_store.artifact_ref(
                    overlay_contact_sheet_path,
                    kind="overlay_contact_sheet",
                    mime_type="image/png",
                ),
            )

        manifest_path = run_dir / "manifest.json"
        seed = request.seed if request.seed is not None else request.pipeline.seed
        effective_seeds = (
            [request.seed + index for index in range(request.variants_per_image)]
            if request.seed is not None
            else ([request.pipeline.seed] if request.pipeline.seed is not None else [])
        )
        artifact_counts = Counter(artifact.kind for artifact in artifacts)
        manifest_data: dict[str, Any] = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "inputs": [str(path) for path in source_paths],
            "pipeline": request.pipeline.model_dump(mode="json", exclude_none=True),
            "summary": {
                "input_count": len(source_paths),
                "variants_per_image": request.variants_per_image,
                "seed": seed,
                "effective_seeds": effective_seeds,
                "max_side": request.max_side,
                "transform_count": len(request.pipeline.transforms),
                "transform_names": [transform.name for transform in request.pipeline.transforms],
                "artifact_counts": dict(artifact_counts),
                "contact_sheet_paths": [
                    artifact.path
                    for artifact in artifacts
                    if artifact.kind in {"contact_sheet", "overlay_contact_sheet"}
                ],
                "warnings": [],
                "annotation_observation_count": len(annotation_observations),
            },
            "artifacts": [artifact.model_dump(mode="json") for artifact in artifacts],
            "annotation_observations": [
                observation.model_dump(mode="json", exclude_none=True) for observation in annotation_observations
            ],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2, sort_keys=True), encoding="utf-8")
        self.artifact_store.record_run(manifest_data)
        manifest = self.artifact_store.artifact_ref(manifest_path, kind="manifest", mime_type="application/json")
        return PreviewResult(
            run_id=run_id,
            artifacts=artifacts,
            manifest=manifest,
            pipeline=request.pipeline.model_dump(mode="json", exclude_none=True),
        )

    def compare_preview_runs(self, baseline_run_id: str, candidate_run_id: str) -> PreviewRunComparison:
        """Compare two recorded preview manifests."""
        baseline = self.artifact_store.read_manifest(baseline_run_id)
        candidate = self.artifact_store.read_manifest(candidate_run_id)
        comparison = compare_preview_manifests(baseline, candidate)
        quality_summary, quality_warnings = compare_manifest_quality(baseline, candidate)
        return comparison.model_copy(
            update={
                "quality_summary": quality_summary,
                "quality_warnings": quality_warnings,
            },
        )

    @staticmethod
    def _resolve_annotations(request: PreviewRequest) -> list[Any]:
        if request.annotations is None:
            return [None] * len(request.input_paths)
        if len(request.annotations) != len(request.input_paths):
            msg = "annotations length must match input_paths length"
            raise ValueError(msg)
        return request.annotations

    @staticmethod
    def _load_rgb(path: Path, max_side: int) -> tuple[Image.Image, tuple[int, int]]:
        image = Image.open(path).convert("RGB")
        original_size = image.size
        image.thumbnail((max_side, max_side))
        return image, original_size

    @staticmethod
    def _annotation_observation(
        *,
        image_index: int,
        variant_index: int,
        annotation: Any,
        input_mask: Any,
        result: dict[str, Any],
    ) -> AnnotationObservation:
        return AnnotationObservation(
            image_index=image_index,
            variant_index=variant_index,
            input_bbox_count=len(annotation.bboxes),
            output_bbox_count=len(result.get("bboxes") or []),
            input_keypoint_count=len(annotation.keypoints),
            output_keypoint_count=len(result.get("keypoints") or []),
            input_mask_coverage=_mask_coverage(input_mask),
            output_mask_coverage=_mask_coverage(result.get("mask")),
        )

    @staticmethod
    def _write_contact_sheet(image_paths: list[Path], output_path: Path) -> None:
        images = [Image.open(path).convert("RGB") for path in image_paths]
        if not images:
            Image.new("RGB", (1, 1), "white").save(output_path)
            return

        tile_width = max(image.width for image in images)
        tile_height = max(image.height for image in images)
        columns = math.ceil(math.sqrt(len(images)))
        rows = math.ceil(len(images) / columns)
        sheet = Image.new("RGB", (columns * tile_width, rows * tile_height), "white")

        for index, image in enumerate(images):
            column = index % columns
            row = index // columns
            sheet.paste(image, (column * tile_width, row * tile_height))

        sheet.save(output_path)


def _mask_coverage(mask: Any) -> float | None:
    if mask is None:
        return None
    data = np.asarray(mask)
    if data.size == 0:
        return None
    return round(float((data > 0).mean()), 6)
