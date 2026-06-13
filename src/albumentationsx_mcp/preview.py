"""Preview rendering with scoped filesystem access."""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from PIL import Image

from albumentationsx_mcp.models import (
    ArtifactKind,
    ArtifactRef,
    ComposeSpec,
    PreviewRequest,
    PreviewResult,
    PreviewRunSummary,
)

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

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"

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
        existing = [run for run in self.list_runs(limit=100) if run.run_id != run_id]
        payload = {
            "runs": [summary.model_dump(mode="json"), *[run.model_dump(mode="json") for run in existing]][:100],
        }
        self.index_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def list_runs(self, limit: int = 20) -> list[PreviewRunSummary]:
        """Return recent preview run summaries, newest first."""
        if not self.index_path.exists():
            return []
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        return [PreviewRunSummary.model_validate(item) for item in payload.get("runs", [])[: max(0, limit)]]

    def read_manifest(self, run_id: str) -> dict[str, Any]:
        """Read a preview manifest by run id without allowing path traversal."""
        if not _RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError(f"Invalid preview run id: {run_id}")
        manifest_path = self.root / run_id / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(manifest_path)
        return json.loads(manifest_path.read_text(encoding="utf-8"))


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
        source_paths = [self.path_policy.resolve_input(path) for path in request.input_paths]

        for source_index, source_path in enumerate(source_paths):
            image = self._load_rgb(source_path, request.max_side)
            for variant_index in range(request.variants_per_image):
                pipeline = request.pipeline.model_copy(deep=True)
                if request.seed is not None:
                    pipeline.seed = request.seed + variant_index
                transform = self.pipeline_service.build_pipeline(pipeline)
                result = transform(image=np.asarray(image))["image"]
                output = run_dir / f"{source_index:03d}-{variant_index:03d}.png"
                Image.fromarray(result).save(output)
                artifacts.append(self.artifact_store.artifact_ref(output, kind="image", mime_type="image/png"))

        contact_sheet_path = run_dir / "contact_sheet.png"
        self._write_contact_sheet([Path(artifact.path) for artifact in artifacts], contact_sheet_path)
        artifacts.append(
            self.artifact_store.artifact_ref(
                contact_sheet_path,
                kind="contact_sheet",
                mime_type="image/png",
            ),
        )

        manifest_path = run_dir / "manifest.json"
        manifest_data: dict[str, Any] = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "inputs": [str(path) for path in source_paths],
            "pipeline": request.pipeline.model_dump(mode="json", exclude_none=True),
            "artifacts": [artifact.model_dump(mode="json") for artifact in artifacts],
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

    @staticmethod
    def _load_rgb(path: Path, max_side: int) -> Image.Image:
        image = Image.open(path).convert("RGB")
        image.thumbnail((max_side, max_side))
        return image

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
