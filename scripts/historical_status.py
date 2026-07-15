"""Shared historical-state banner for archived generated Markdown."""

from __future__ import annotations

HISTORICAL_STATUS_BANNER = (
    "> **Historical status snapshot.** This document preserves a pre-release decision and does not describe the "
    "current published release. See [STATUS.md](STATUS.md)."
)


def add_historical_status_banner(markdown: str) -> str:
    """Insert the historical-state warning after the first Markdown heading."""
    if HISTORICAL_STATUS_BANNER in markdown:
        return markdown
    title, separator, remainder = markdown.partition("\n")
    if not separator or not title.startswith("# "):
        msg = "historical Markdown must start with an H1"
        raise ValueError(msg)
    return f"{title}\n\n{HISTORICAL_STATUS_BANNER}\n\n{remainder.lstrip()}"
