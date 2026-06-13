"""JSON-backed review feedback journal for preview examples."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from albumentationsx_mcp.models import PreviewFeedbackList, PreviewFeedbackRecord

_FEEDBACK_FILE = "preview_feedback.json"


class PreviewFeedbackStore:
    """Small local journal for concrete preview example feedback."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / _FEEDBACK_FILE

    def record_feedback(  # noqa: PLR0913
        self,
        *,
        run_id: str,
        image_index: int,
        variant_index: int,
        feedback_tags: list[str],
        note: str = "",
        accepted: bool = False,
    ) -> PreviewFeedbackRecord:
        """Persist one user feedback item for a concrete preview image variant."""
        normalized_tags = _normalize_tags(feedback_tags)
        if not accepted and not normalized_tags:
            msg = "feedback_tags must contain at least one tag unless accepted is true"
            raise ValueError(msg)
        feedback = PreviewFeedbackRecord(
            feedback_id=uuid.uuid4().hex,
            created_at=_utc_now(),
            run_id=run_id,
            image_index=image_index,
            variant_index=variant_index,
            feedback_tags=normalized_tags,
            note=note.strip(),
            accepted=accepted,
            review_target=f"example {image_index + 1} / variant {variant_index + 1}",
            recommended_next_tool="record_tuning_decision" if accepted else "adjust_pipeline",
        )
        records = [feedback, *self._read_feedback()]
        self._write_feedback(records)
        return feedback

    def list_feedback(
        self,
        *,
        run_id: str | None = None,
        limit: int = 20,
        accepted_only: bool = False,
    ) -> PreviewFeedbackList:
        """Return newest-first concrete preview feedback records."""
        records = self._read_feedback()
        if run_id is not None:
            records = [record for record in records if record.run_id == run_id]
        total_count = len(records)
        accepted_count = sum(record.accepted for record in records)
        if accepted_only:
            records = [record for record in records if record.accepted]
        bounded_limit = max(1, min(limit, 100))
        returned = records[:bounded_limit]
        return PreviewFeedbackList(
            feedback=returned,
            total_count=total_count,
            accepted_count=accepted_count,
            run_id=run_id,
            accepted_only=accepted_only,
            aggregated_feedback_tags=_aggregate_tags(returned),
        )

    def _read_feedback(self) -> list[PreviewFeedbackRecord]:
        if not self.index_path.exists():
            return []
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        return [PreviewFeedbackRecord.model_validate(item) for item in payload.get("feedback", [])]

    def _write_feedback(self, records: list[PreviewFeedbackRecord]) -> None:
        payload = {"feedback": [record.model_dump(mode="json") for record in records]}
        self.index_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _normalize_tags(feedback_tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in feedback_tags:
        clean_tag = tag.strip()
        if clean_tag and clean_tag not in seen:
            normalized.append(clean_tag)
            seen.add(clean_tag)
    return normalized


def _aggregate_tags(records: list[PreviewFeedbackRecord]) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for record in records:
        for tag in record.feedback_tags:
            if tag not in seen:
                tags.append(tag)
                seen.add(tag)
    return tags


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
