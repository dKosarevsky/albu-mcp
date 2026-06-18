"""Generate small static demo assets for README and usage documentation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def render_demo_assets(output_dir: Path) -> Path:
    """Render deterministic demo images and return the manifest path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = output_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    sample = _build_sample_image()
    sample_path = inputs_dir / "sample-grid.png"
    sample.save(sample_path)

    baseline_variants = [
        sample,
        sample.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
        sample.rotate(4, resample=Image.Resampling.BICUBIC, fillcolor="white"),
    ]
    candidate_variants = [
        sample.filter(ImageFilter.SHARPEN),
        sample.transpose(Image.Transpose.FLIP_LEFT_RIGHT).filter(ImageFilter.SMOOTH),
        sample.rotate(2, resample=Image.Resampling.BICUBIC, fillcolor="white"),
    ]

    contact_sheet_path = output_dir / "contact_sheet.png"
    comparison_path = output_dir / "comparison_contact_sheet.png"
    report_path = output_dir / "demo_report.md"
    _write_contact_sheet(baseline_variants, contact_sheet_path, labels=["baseline 1", "baseline 2", "baseline 3"])
    _write_contact_sheet(
        [*baseline_variants, *candidate_variants],
        comparison_path,
        labels=[
            "baseline 1",
            "baseline 2",
            "baseline 3",
            "candidate 1",
            "candidate 2",
            "candidate 3",
        ],
        columns=3,
    )

    manifest_path = output_dir / "demo_manifest.json"
    manifest = {
        "workflow": (
            "recommend_pipeline -> render_preview_batch -> adjust_pipeline -> compare_preview_runs -> export_pipeline"
        ),
        "input": str(sample_path),
        "contact_sheet": str(contact_sheet_path),
        "comparison_contact_sheet": str(comparison_path),
        "baseline_pipeline": {
            "transforms": [
                {"name": "HorizontalFlip", "p": 0.2},
                {"name": "RandomBrightnessContrast", "p": 0.2},
                {"name": "GaussNoise", "params": {"std_range": [0.02, 0.1]}, "p": 0.1},
            ],
            "seed": 137,
        },
        "candidate_pipeline": {
            "transforms": [
                {"name": "HorizontalFlip", "p": 0.2},
                {"name": "RandomBrightnessContrast", "p": 0.2},
                {"name": "GaussNoise", "params": {"std_range": [0.01, 0.05]}, "p": 0.05},
            ],
            "seed": 147,
        },
        "compare_preview_runs": {
            "review_note": "Candidate keeps the object readable while reducing noise severity.",
            "feedback_tags": ["too_noisy"],
        },
    }
    _write_demo_report(report_path)
    manifest["demo_report"] = str(report_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def _build_sample_image() -> Image.Image:
    image = Image.new("RGB", (160, 120), "white")
    draw = ImageDraw.Draw(image)
    for x in range(0, 160, 20):
        draw.line([(x, 0), (x, 120)], fill=(220, 220, 220), width=1)
    for y in range(0, 120, 20):
        draw.line([(0, y), (160, y)], fill=(220, 220, 220), width=1)
    draw.rectangle((42, 28, 118, 92), outline=(25, 75, 130), width=4, fill=(187, 219, 245))
    draw.ellipse((66, 46, 94, 74), outline=(160, 48, 48), width=4, fill=(248, 205, 205))
    draw.text((47, 96), "sample object", fill=(30, 30, 30))
    return image


def _write_contact_sheet(
    images: list[Image.Image],
    output_path: Path,
    *,
    labels: list[str],
    columns: int | None = None,
) -> None:
    columns = columns or len(images)
    tile_width = max(image.width for image in images)
    tile_height = max(image.height for image in images) + 18
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile_width, rows * tile_height), "white")
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(images):
        column = index % columns
        row = index // columns
        x = column * tile_width
        y = row * tile_height
        sheet.paste(image, (x, y))
        draw.text((x + 4, y + image.height + 3), labels[index], fill=(30, 30, 30))
    sheet.save(output_path)


def _write_demo_report(output_path: Path) -> None:
    output_path.write_text(
        """# AlbumentationsX MCP Demo Report

## Baseline

![Baseline contact sheet](contact_sheet.png)

## Candidate

![Comparison contact sheet](comparison_contact_sheet.png)

## Review

- Feedback tag: `too_noisy`
- Adjustment: reduce `GaussNoise` probability and noise range.
- Decision: Candidate accepted for a small robustness pass.
""",
        encoding="utf-8",
    )


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Generate demo contact sheets for AlbumentationsX MCP docs.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/assets/demo"))
    args = parser.parse_args()
    manifest_path = render_demo_assets(args.output_dir)
    sys.stdout.write(f"wrote {manifest_path}\n")


if __name__ == "__main__":
    main()
