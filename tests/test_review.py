from pathlib import Path

import pytest

from albumentationsx_mcp.review import PreviewFeedbackStore


def test_preview_feedback_store_records_example_feedback_newest_first(tmp_path: Path) -> None:
    store = PreviewFeedbackStore(tmp_path)

    older = store.record_feedback(
        run_id="candidate-a",
        image_index=7,
        variant_index=0,
        feedback_tags=["too_noisy:high"],
        note="example 8 is too noisy",
    )
    newer = store.record_feedback(
        run_id="candidate-a",
        image_index=1,
        variant_index=0,
        feedback_tags=["too_blurry"],
        note="example 2 lost edges",
    )
    listed = store.list_feedback(run_id="candidate-a")

    assert older.review_target == "example 8 / variant 1"
    assert older.recommended_next_tool == "adjust_pipeline"
    assert older.feedback_tags == ["too_noisy:high"]
    assert newer.created_at.endswith("Z")
    assert [record.feedback_id for record in listed.feedback] == [newer.feedback_id, older.feedback_id]
    assert listed.total_count == 2
    assert listed.accepted_count == 0
    assert listed.aggregated_feedback_tags == ["too_blurry", "too_noisy:high"]
    assert (tmp_path / "preview_feedback.json").exists()


def test_preview_feedback_store_lists_accepted_feedback(tmp_path: Path) -> None:
    store = PreviewFeedbackStore(tmp_path)
    store.record_feedback(
        run_id="candidate-a",
        image_index=0,
        variant_index=0,
        feedback_tags=["too_noisy"],
        note="too strong",
    )
    accepted = store.record_feedback(
        run_id="candidate-a",
        image_index=2,
        variant_index=0,
        feedback_tags=[],
        note="example 3 is usable",
        accepted=True,
    )

    listed = store.list_feedback(run_id="candidate-a", accepted_only=True)

    assert listed.total_count == 2
    assert listed.accepted_count == 1
    assert listed.feedback == [accepted]
    assert accepted.recommended_next_tool == "record_tuning_decision"
    assert listed.aggregated_feedback_tags == []


def test_preview_feedback_store_rejects_negative_feedback_without_tags(tmp_path: Path) -> None:
    store = PreviewFeedbackStore(tmp_path)

    with pytest.raises(ValueError, match="feedback_tags"):
        store.record_feedback(
            run_id="candidate-a",
            image_index=0,
            variant_index=0,
            feedback_tags=[],
            note="too strong but no tag",
        )
