from __future__ import annotations

from pathlib import Path

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
