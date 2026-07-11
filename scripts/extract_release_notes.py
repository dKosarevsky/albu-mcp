"""Extract one release's notes from CHANGELOG.md for GitHub Release publishing."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_RELEASE_HEADING = re.compile(r"(?m)^##[ \t]+(?P<version>\S+)(?:[ \t]+-[^\n]*)?[ \t]*$")


def extract_release_notes(changelog: str, *, tag: str) -> str:
    """Return the non-empty changelog body matching an exact v-prefixed tag."""
    version = _version_from_tag(tag)
    headings = list(_RELEASE_HEADING.finditer(changelog))
    for index, heading in enumerate(headings):
        if heading.group("version") != version:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(changelog)
        notes = changelog[heading.end() : end].strip()
        if not notes:
            msg = f"CHANGELOG.md release section for {version!r} is empty"
            raise ValueError(msg)
        return notes
    msg = f"CHANGELOG.md does not contain release section for {version!r}"
    raise ValueError(msg)


def write_release_notes(
    *,
    tag: str,
    changelog_path: Path = Path("CHANGELOG.md"),
    output_path: Path | None = None,
) -> str:
    """Extract release notes and optionally write them as a newline-terminated file."""
    notes = extract_release_notes(changelog_path.read_text(encoding="utf-8"), tag=tag)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{notes}\n", encoding="utf-8")
    return notes


def main() -> None:
    """CLI entrypoint used by the release workflow."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Release tag, for example v1.16.0")
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        notes = write_release_notes(
            tag=args.tag,
            changelog_path=args.changelog,
            output_path=args.output,
        )
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc

    if args.output is None:
        sys.stdout.write(f"{notes}\n")
    else:
        sys.stdout.write(f"release notes for {args.tag} written to {args.output}\n")


def _version_from_tag(tag: str) -> str:
    if not tag.startswith("v"):
        msg = "release tag must start with 'v'"
        raise ValueError(msg)
    version = tag[1:]
    if not version:
        msg = "release tag version is empty"
        raise ValueError(msg)
    return version


if __name__ == "__main__":
    main()
