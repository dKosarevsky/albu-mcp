"""Preview rendering with scoped filesystem access."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from albumentationsx_mcp.models import ArtifactKind, ArtifactRef, PreviewRequest, PreviewResult
from albumentationsx_mcp.pipeline import PipelineService


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


class PreviewService:
    """Render deterministic preview images for a pipeline spec."""

    def __init__(
        self,
        pipeline_service: PipelineService,
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

        manifest_path = run_dir / "manifest.json"
        manifest_data: dict[str, Any] = {
            "run_id": run_id,
            "inputs": [str(path) for path in source_paths],
            "pipeline": request.pipeline.model_dump(mode="json", exclude_none=True),
            "artifacts": [artifact.model_dump(mode="json") for artifact in artifacts],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2, sort_keys=True), encoding="utf-8")
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
