"""Check that the committed host acceptance evidence report is up to date."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_host_acceptance_report import build_host_acceptance_report, dump_host_acceptance_markdown

_DEFAULT_REPORT_PATH = Path("docs/HOST_ACCEPTANCE_EVIDENCE.md")


@dataclass(frozen=True)
class HostAcceptanceReportCheck:
    """Result of comparing generated host acceptance evidence with a committed artifact."""

    ok: bool
    expected_path: Path
    message: str


def check_host_acceptance_report(
    *,
    root: Path = Path(),
    report_path: Path = _DEFAULT_REPORT_PATH,
) -> HostAcceptanceReportCheck:
    """Return whether the host acceptance evidence report matches current repo metadata."""
    expected = dump_host_acceptance_markdown(build_host_acceptance_report(root))
    if not report_path.exists():
        return HostAcceptanceReportCheck(
            ok=False,
            expected_path=report_path,
            message=_stale_message(report_path, reason="is missing"),
        )

    actual = report_path.read_text(encoding="utf-8")
    if actual != expected:
        return HostAcceptanceReportCheck(
            ok=False,
            expected_path=report_path,
            message=_stale_message(report_path, reason="is stale"),
        )

    return HostAcceptanceReportCheck(
        ok=True,
        expected_path=report_path,
        message=f"host acceptance evidence is fresh: {report_path}",
    )


def main() -> None:
    """CLI entrypoint for CI freshness checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(), help="Repository root. Defaults to cwd.")
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Generated Markdown report path.",
    )
    args = parser.parse_args()

    report_path = args.report if args.report is not None else args.root / _DEFAULT_REPORT_PATH
    result = check_host_acceptance_report(root=args.root, report_path=report_path)
    if not result.ok:
        sys.stderr.write(f"{result.message}\n")
        raise SystemExit(1)
    sys.stdout.write(f"{result.message}\n")


def _stale_message(report_path: Path, *, reason: str) -> str:
    return (
        f"Host acceptance evidence {reason}: {report_path}. "
        "Regenerate it with: uv run python scripts/export_host_acceptance_report.py "
        f"--output {report_path}"
    )


if __name__ == "__main__":
    main()
