"""Export a gated 100-iteration product governor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_FIRST_GOALS = [
    ("evidence", "Close P0 real-host evidence for Codex and Claude Code."),
    ("release", "Open the RC gate only after P0 and beta evidence pass."),
    ("beta", "Collect one privacy-safe beta attempt for every workflow."),
    ("product", "Implement the first policy assistant slice after gates open."),
    ("distribution", "Prepare post-RC distribution and registry follow-up."),
]
_LANES = ("evidence", "release", "beta", "product", "distribution", "quality", "docs", "adoption")


def build_product_iteration_governor() -> dict[str, Any]:
    """Build 100 sequenced goals without authorizing blind implementation."""
    iterations = [_iteration(index) for index in range(1, 101)]
    return {
        "governor_status": "sequenced_not_auto_executed",
        "iteration_count": len(iterations),
        "execution_policy": "Each iteration needs a named goal, tests, readiness checks, and evidence gates before merge.",
        "safety_policy": "No blind 100-iteration implementation loop is allowed.",
        "required_checks": [
            "uv run pytest -q",
            "uv run ruff check .",
            "uv run ruff format --check .",
            "uv run ty check",
            "uv run python scripts/check_release_readiness.py",
        ],
        "iterations": iterations,
        "source_docs": [
            "docs/REAL_HOST_EVIDENCE_COMMAND_CENTER.md",
            "docs/RC_EVIDENCE_REOPEN_FLOW.md",
            "docs/BETA_VALIDATION_LOOP.md",
            "docs/POLICY_ASSISTANT_PLAN.md",
        ],
    }


def render_product_iteration_governor_markdown(governor: dict[str, Any]) -> str:
    """Render the product iteration governor as Markdown."""
    lines = [
        "# Product Iteration Governor",
        "",
        f"Governor status: `{governor['governor_status']}`",
        f"Iteration count: `{governor['iteration_count']}`",
        "",
        "## Execution Policy",
        "",
        governor["execution_policy"],
        governor["safety_policy"],
        "",
        "## Required Checks",
        "",
    ]
    lines.extend(f"- `{command}`" for command in governor["required_checks"])
    lines.extend(
        [
            "",
            "## Iteration Queue",
            "",
            "| Iteration | Lane | Status | Goal |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| {item['iteration']} | `{item['lane']}` | `{item['status']}` | {item['goal']} |"
        for item in governor["iterations"]
    )
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in governor["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for product iteration governor exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_product_iteration_governor_markdown(build_product_iteration_governor())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _iteration(index: int) -> dict[str, Any]:
    if index <= len(_FIRST_GOALS):
        lane, goal = _FIRST_GOALS[index - 1]
    else:
        lane = _LANES[(index - 1) % len(_LANES)]
        goal = _generated_goal(index=index, lane=lane)
    return {
        "iteration": index,
        "goal": goal,
        "lane": lane,
        "status": "current_priority" if index == 1 else "blocked_until_previous_iteration",
    }


def _generated_goal(*, index: int, lane: str) -> str:
    return f"Run product iteration {index} in the {lane} lane with tests, evidence, and readiness checks."


if __name__ == "__main__":
    main()
