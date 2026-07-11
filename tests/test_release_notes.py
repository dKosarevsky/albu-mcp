from __future__ import annotations

from pathlib import Path

import pytest

from scripts.extract_release_notes import extract_release_notes, write_release_notes

_CHANGELOG = """\
# Changelog

## Unreleased

- A future change.

## 1.16.0 - 2026-07-11

- Accept a single image.
- Strengthen weak exposure safely.

### Evidence boundary

Generated fixtures are not adoption evidence.

## 1.15.0 - 2026-06-23

- Previous release.
"""


def test_extract_release_notes_returns_only_matching_version_section() -> None:
    notes = extract_release_notes(_CHANGELOG, tag="v1.16.0")

    assert notes == (
        "- Accept a single image.\n"
        "- Strengthen weak exposure safely.\n\n"
        "### Evidence boundary\n\n"
        "Generated fixtures are not adoption evidence."
    )
    assert "future change" not in notes
    assert "Previous release" not in notes


@pytest.mark.parametrize(
    ("tag", "changelog", "message"),
    [
        ("1.16.0", _CHANGELOG, "tag must start with 'v'"),
        ("v9.9.9", _CHANGELOG, "does not contain release section"),
        ("v1.16.0", "# Changelog\n\n## 1.16.0 - 2026-07-11\n\n## 1.15.0\n\n- Old.\n", "is empty"),
    ],
)
def test_extract_release_notes_rejects_invalid_release_sections(tag: str, changelog: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        extract_release_notes(changelog, tag=tag)


def test_write_release_notes_writes_exact_section(tmp_path: Path) -> None:
    changelog_path = tmp_path / "CHANGELOG.md"
    output_path = tmp_path / "release-notes.md"
    changelog_path.write_text(_CHANGELOG, encoding="utf-8")

    notes = write_release_notes(
        tag="v1.16.0",
        changelog_path=changelog_path,
        output_path=output_path,
    )

    assert output_path.read_text(encoding="utf-8") == f"{notes}\n"
