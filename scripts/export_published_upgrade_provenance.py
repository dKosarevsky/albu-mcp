"""Export canonical provenance for a public published-upgrade workflow report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from albumentationsx_mcp.published_provenance import (
    build_published_upgrade_provenance,
    serialize_published_upgrade_provenance,
)
from albumentationsx_mcp.upgrade_proof import MAX_UPGRADE_PROOF_REPORT_BYTES
from scripts.check_published_upgrade import write_atomic_text

_WORKFLOW_PATH = ".github/workflows/published-upgrade-proof.yml"
_ARTIFACT_NAME = "published-upgrade-proof"
_ARTIFACT_FILE = "published-upgrade-proof.json"
_EXPORT_ERROR = "published upgrade provenance export failed"


def main() -> None:
    """Validate CLI inputs and write one canonical provenance sidecar."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow-ref", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-head-sha", required=True)
    parser.add_argument("--verified-on", required=True)
    parser.add_argument(
        "--verification-method",
        choices=("downloaded_artifact", "workflow_output"),
        required=True,
    )
    parser.add_argument("--artifact-retention-days", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        evidence = _read_bounded(args.evidence)
        provenance = build_published_upgrade_provenance(
            evidence=evidence,
            repository=args.repository,
            workflow_path=_WORKFLOW_PATH,
            workflow_ref=args.workflow_ref,
            run_id=args.run_id,
            run_head_sha=args.run_head_sha,
            artifact_name=_ARTIFACT_NAME,
            artifact_file=_ARTIFACT_FILE,
            artifact_retention_days=args.artifact_retention_days,
            verified_on=args.verified_on,
            verification_method=args.verification_method,
        )
        write_atomic_text(args.output, serialize_published_upgrade_provenance(provenance))
    except (OSError, RuntimeError, TypeError, ValueError):
        sys.stderr.write(f"{_EXPORT_ERROR}\n")
        raise SystemExit(2) from None
    sys.stdout.write(f"wrote verified provenance to {args.output}\n")


def _read_bounded(path: Path) -> bytes:
    if not path.is_file() or path.stat().st_size > MAX_UPGRADE_PROOF_REPORT_BYTES:
        raise ValueError
    content = path.read_bytes()
    if len(content) > MAX_UPGRADE_PROOF_REPORT_BYTES:
        raise ValueError
    return content


if __name__ == "__main__":
    main()
