"""Export stable v1 release train gates and publish sequence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_v1_trust_gates import build_v1_trust_gates


def build_v1_release_train() -> dict[str, Any]:
    """Build the stable v1 release train checklist from current trust gates."""
    trust = build_v1_trust_gates()
    manual_gate_count = len(trust["manual_gates"])
    return {
        "package": trust["package"],
        "current_version": trust["package_version"],
        "release_allowed": trust["ready_for_v1"] and manual_gate_count == 0,
        "manual_gate_count": manual_gate_count,
        "pre_release_steps": [
            "uv run pytest",
            "uv run ruff check .",
            "uv run ruff format --check .",
            "uv run ty check",
            "uv run python scripts/export_v1_trust_gates.py --output docs/V1_TRUST_GATES.md",
            "uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md",
            "uv run python scripts/check_release_readiness.py",
            "uv run python scripts/run_golden_evals.py",
            "uv build",
        ],
        "publish_steps": [
            "git tag v<next-version>",
            "git push origin v<next-version>",
            "gh release create v<next-version> --verify-tag --notes-file CHANGELOG.md",
            "wait for GitHub release workflow and PyPI Trusted Publishing",
            "run MCP Registry publish workflow after PyPI is visible",
        ],
        "post_release_steps": [
            "uvx --from albumentationsx-mcp==<next-version> albumentationsx-mcp --help",
            "uv run python scripts/check_mcp_registry_status.py",
            "uv run python scripts/check_directory_presence.py",
            "uv run python scripts/export_network_growth_tracker.py --output docs/NETWORK_GROWTH_TRACKER.md",
        ],
    }


def render_v1_release_train_markdown(train: dict[str, Any]) -> str:
    """Render stable v1 release train checklist as Markdown."""
    decision = (
        "Stable v1 release train can proceed after the final verification run."
        if train["release_allowed"]
        else "Do not publish a stable v1 release until all manual host evidence gates pass."
    )
    lines = [
        "# V1 Release Train",
        "",
        f"Package: `{train['package']}=={train['current_version']}`",
        f"Release allowed: `{str(train['release_allowed']).lower()}`",
        f"Manual gate count: `{train['manual_gate_count']}`",
        "",
        "## Decision",
        "",
        decision,
        "",
        "## Pre-Release Steps",
        "",
        *[f"- `{step}`" for step in train["pre_release_steps"]],
        "",
        "## Publish Steps",
        "",
        *[f"- `{step}`" for step in train["publish_steps"]],
        "",
        "## Post-Release Steps",
        "",
        *[f"- `{step}`" for step in train["post_release_steps"]],
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for stable v1 release train exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_v1_release_train_markdown(build_v1_release_train())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
