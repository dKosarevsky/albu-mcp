"""Check that committed public contract snapshots are up to date."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.classify_contract_drift import classify_contract_drift
from scripts.export_mcp_contract import build_contract_snapshot, dump_contract_snapshot
from scripts.export_output_contracts import build_output_contract_snapshot, dump_output_contract_snapshot

_DEFAULT_MCP_SNAPSHOT_PATH = Path("tests/fixtures/snapshots/mcp_contract.json")
_DEFAULT_OUTPUT_SNAPSHOT_PATH = Path("tests/fixtures/snapshots/output_contracts.json")


@dataclass(frozen=True)
class ContractSnapshotCheck:
    """Result for one generated-vs-committed contract snapshot comparison."""

    name: str
    path: Path
    ok: bool
    message: str
    diff: str = ""


@dataclass(frozen=True)
class ContractSnapshotReport:
    """Aggregate result for all public contract snapshot checks."""

    checks: list[ContractSnapshotCheck]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)


def check_contract_snapshots(
    *,
    mcp_snapshot_path: Path = _DEFAULT_MCP_SNAPSHOT_PATH,
    output_snapshot_path: Path = _DEFAULT_OUTPUT_SNAPSHOT_PATH,
    output_work_dir: Path | None = None,
) -> ContractSnapshotReport:
    """Compare committed public contract snapshots with freshly generated snapshots."""
    if output_work_dir is None:
        with tempfile.TemporaryDirectory(prefix="albu-contract-snapshots-") as tmp_dir:
            return _check_contract_snapshots(
                mcp_snapshot_path=mcp_snapshot_path,
                output_snapshot_path=output_snapshot_path,
                output_work_dir=Path(tmp_dir),
            )
    return _check_contract_snapshots(
        mcp_snapshot_path=mcp_snapshot_path,
        output_snapshot_path=output_snapshot_path,
        output_work_dir=output_work_dir,
    )


def main() -> None:
    """CLI entrypoint for CI and release snapshot freshness checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcp-snapshot", type=Path, default=_DEFAULT_MCP_SNAPSHOT_PATH)
    parser.add_argument("--output-snapshot", type=Path, default=_DEFAULT_OUTPUT_SNAPSHOT_PATH)
    parser.add_argument("--output-work-dir", type=Path, default=None)
    args = parser.parse_args()

    report = check_contract_snapshots(
        mcp_snapshot_path=args.mcp_snapshot,
        output_snapshot_path=args.output_snapshot,
        output_work_dir=args.output_work_dir,
    )
    if not report.ok:
        for check in report.checks:
            if check.ok:
                continue
            sys.stderr.write(f"{check.message}\n")
            if check.diff:
                sys.stderr.write(check.diff)
        raise SystemExit(1)
    checked = ", ".join(str(check.path) for check in report.checks)
    sys.stdout.write(f"contract snapshots are fresh: {checked}\n")


def _check_contract_snapshots(
    *,
    mcp_snapshot_path: Path,
    output_snapshot_path: Path,
    output_work_dir: Path,
) -> ContractSnapshotReport:
    output_work_dir.mkdir(parents=True, exist_ok=True)
    mcp_expected = dump_contract_snapshot(build_contract_snapshot())
    output_expected = dump_output_contract_snapshot(build_output_contract_snapshot(output_work_dir))
    return ContractSnapshotReport(
        checks=[
            _compare_snapshot(
                name="mcp_contract",
                label="MCP contract snapshot",
                path=mcp_snapshot_path,
                expected=mcp_expected,
                regenerate_command=f"uv run python scripts/export_mcp_contract.py --output {mcp_snapshot_path}",
            ),
            _compare_snapshot(
                name="output_contracts",
                label="Output contract snapshot",
                path=output_snapshot_path,
                expected=output_expected,
                regenerate_command=f"uv run python scripts/export_output_contracts.py --output {output_snapshot_path}",
            ),
        ]
    )


def _compare_snapshot(
    *,
    name: str,
    label: str,
    path: Path,
    expected: str,
    regenerate_command: str,
) -> ContractSnapshotCheck:
    if not path.exists():
        return ContractSnapshotCheck(
            name=name,
            path=path,
            ok=False,
            message=f"{label} is missing: {path}. Regenerate it with: {regenerate_command}",
        )
    actual = path.read_text(encoding="utf-8")
    if actual == expected:
        return ContractSnapshotCheck(name=name, path=path, ok=True, message=f"{label} is fresh: {path}")
    return ContractSnapshotCheck(
        name=name,
        path=path,
        ok=False,
        message=(
            f"{label} is stale: {path} "
            f"(classification: {_classify_json_drift(actual=actual, expected=expected)}). "
            f"Regenerate it with: {regenerate_command}"
        ),
        diff=_unified_diff(path=path, actual=actual, expected=expected),
    )


def _classify_json_drift(*, actual: str, expected: str) -> str:
    try:
        return classify_contract_drift(json.loads(actual), json.loads(expected)).kind
    except json.JSONDecodeError:
        return "unclassified"


def _unified_diff(*, path: Path, actual: str, expected: str) -> str:
    return "".join(
        difflib.unified_diff(
            actual.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            fromfile=f"{path} (committed)",
            tofile=f"{path} (generated)",
        )
    )


if __name__ == "__main__":
    main()
