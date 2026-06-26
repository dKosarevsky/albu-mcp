from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_beta_workflow_pack import build_beta_workflow_pack, render_beta_workflow_pack_markdown


def test_beta_workflow_pack_contains_three_cv_workflows() -> None:
    pack = build_beta_workflow_pack()

    assert [workflow["id"] for workflow in pack["workflows"]] == [
        "robustness_distortion_variants",
        "noisy_preview_tuning",
        "dataset_health_before_training",
    ]
    assert pack["workflows"][0]["target_user"] == "CV engineer preparing robustness data"
    assert "render_preview_batch" in pack["workflows"][0]["mcp_flow"]
    assert "interpret_preview_feedback" in pack["workflows"][1]["mcp_flow"]
    assert "inspect_dataset_quality" in pack["workflows"][2]["mcp_flow"]
    assert all(workflow["privacy_boundary"] == "local paths only; no dataset upload" for workflow in pack["workflows"])
    assert "docs/REAL_HOST_EVIDENCE_EXECUTION.md" in pack["trial_inputs"]


def test_beta_workflow_pack_markdown_is_copyable() -> None:
    markdown = render_beta_workflow_pack_markdown(build_beta_workflow_pack())

    assert markdown.startswith("# Beta Workflow Pack\n")
    assert "## Trial Inputs" in markdown
    assert "### robustness_distortion_variants" in markdown
    assert "Make varied distorted previews for robustness review." in markdown
    assert "### noisy_preview_tuning" in markdown
    assert "Interpret free-form feedback and plan a safer adjustment." in markdown
    assert "### dataset_health_before_training" in markdown
    assert "Inspect annotations before augmentation preview work." in markdown
    assert "## Success Criteria" in markdown
    assert "User can reject an over-noisy candidate without reading docs." in markdown


def test_committed_beta_workflow_pack_is_current() -> None:
    pack_path = Path("docs/BETA_WORKFLOW_PACK.md")

    assert pack_path.read_text(encoding="utf-8") == render_beta_workflow_pack_markdown(build_beta_workflow_pack())
    assert "[docs/BETA_WORKFLOW_PACK.md](docs/BETA_WORKFLOW_PACK.md)" in Path("README.md").read_text(encoding="utf-8")


def test_beta_workflow_pack_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "beta-workflow-pack.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_beta_workflow_pack.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Beta Workflow Pack\n")
