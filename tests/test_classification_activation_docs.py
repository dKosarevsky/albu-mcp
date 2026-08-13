from __future__ import annotations

from pathlib import Path

import pytest
import yaml

USE_CASE_PATH = Path("docs/use-cases/CLASSIFICATION_ROBUSTNESS.md")


def test_classification_use_case_is_a_complete_activation_path() -> None:
    guide = USE_CASE_PATH.read_text(encoding="utf-8")

    assert "../assets/demo/comparison_contact_sheet.png" in guide
    assert "releases/latest/download/albumentationsx-mcp.mcpb" in guide
    assert "uvx --from albumentationsx-mcp albumentationsx-mcp" in guide
    assert "run_host_smoke_check" in guide
    assert "run_first_preview" in guide
    assert "trace_preview_variant" in guide
    assert "too_noisy:high" in guide
    assert "render -> reject -> adjust -> accept" in guide
    assert "workflow-feedback.yml" in guide
    assert "https://albumentations.ai/docs/integrations/mcp/" in guide


def test_public_docs_link_one_canonical_classification_use_case() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    index = Path("docs/INDEX.md").read_text(encoding="utf-8")
    destination = "docs/use-cases/CLASSIFICATION_ROBUSTNESS.md"

    assert f"({destination})" in readme
    assert "[use-cases/CLASSIFICATION_ROBUSTNESS.md](use-cases/CLASSIFICATION_ROBUSTNESS.md)" in index
    assert len(readme.splitlines()) <= 100


@pytest.mark.parametrize(
    ("field_id", "expected_options"),
    [
        (
            "campaign",
            {
                "classification-robustness",
                "detection-bbox-safety",
                "segmentation-mask-safety",
                "general-or-not-sure",
            },
        ),
        (
            "discovery_source",
            {
                "official-albumentations-docs",
                "albumentations-discord",
                "x-twitter",
                "github",
                "mcp-registry",
                "pypi",
                "skills-sh",
                "other-or-not-sure",
            },
        ),
        (
            "install_route",
            {
                "claude-desktop-mcpb",
                "uvx",
                "pip",
                "source-checkout",
                "other-or-not-sure",
            },
        ),
        (
            "workflow_outcome",
            {
                "accepted-after-adjustment",
                "accepted-first-render",
                "blocked-before-render",
                "unresolved-after-adjustment",
            },
        ),
    ],
)
def test_workflow_feedback_collects_bounded_activation_fields(
    field_id: str,
    expected_options: set[str],
) -> None:
    template = yaml.safe_load(Path(".github/ISSUE_TEMPLATE/workflow-feedback.yml").read_text(encoding="utf-8"))
    field = next(item for item in template["body"] if item.get("id") == field_id)

    assert set(field["attributes"]["options"]) == expected_options


def test_feedback_requires_campaign_and_outcome_without_requesting_identity() -> None:
    template_text = Path(".github/ISSUE_TEMPLATE/workflow-feedback.yml").read_text(encoding="utf-8")
    template = yaml.safe_load(template_text)
    fields = {item.get("id"): item for item in template["body"]}

    assert fields["campaign"]["validations"]["required"] is True
    assert fields["workflow_outcome"]["validations"]["required"] is True
    assert fields["discovery_source"].get("validations", {}).get("required") is not True
    assert fields["install_route"].get("validations", {}).get("required") is not True
    assert "email" not in template_text.lower()
    assert "organization" not in template_text.lower()


def test_feedback_guide_explains_campaign_counting_and_privacy() -> None:
    guide = Path("docs/FIRST_PREVIEW_FEEDBACK.md").read_text(encoding="utf-8")

    assert "accepted-after-adjustment" in guide
    assert "classification-robustness" in guide
    assert "aggregate" in guide.lower()
    assert "No telemetry" in guide
