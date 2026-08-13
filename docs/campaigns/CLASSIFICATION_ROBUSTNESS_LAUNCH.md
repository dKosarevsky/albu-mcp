# Classification Robustness Launch Pack

Campaign: `classification-robustness`

Canonical destination: https://github.com/dKosarevsky/albu-mcp/blob/main/docs/use-cases/CLASSIFICATION_ROBUSTNESS.md

Audience: Classification practitioners testing robustness without destroying label semantics

Problem: Random augmentation policies can make objects unrecognizable before anyone reviews them.

No telemetry, image upload, automated callback, or background publication is enabled.

## Channel Copy

### albumentations-discord

```text
AlbumentationsX MCP now has a focused classification-robustness workflow. Connect a bounded local image folder, render augmentation candidates, reject an excessive result such as too_noisy:high, adjust it, compare both runs, and export only the accepted pipeline. Images stay local and runtime telemetry is disabled. Try it: https://github.com/dKosarevsky/albu-mcp/blob/main/docs/use-cases/CLASSIFICATION_ROBUSTNESS.md
```

### x-twitter

```text
AlbumentationsX MCP: render classification augmentations, reject excessive noise, adjust, compare, and export only an accepted pipeline. Local images stay local; no telemetry. https://github.com/dKosarevsky/albu-mcp/blob/main/docs/use-cases/CLASSIFICATION_ROBUSTNESS.md
```

### generic-community

```text
Try the AlbumentationsX MCP classification-robustness review: one local, reproducible path from preview to rejection, adjustment, comparison, and accepted pipeline export. No image upload or runtime telemetry. https://github.com/dKosarevsky/albu-mcp/blob/main/docs/use-cases/CLASSIFICATION_ROBUSTNESS.md
```

## Feedback CTA

Ask users to submit only deliberate, redacted feedback: https://github.com/dKosarevsky/albu-mcp/issues/new?template=workflow-feedback.yml

A full campaign loop is recorded only as `accepted-after-adjustment`.

## Publication

Policy: `manual only`. Record the real channel URL and timestamp in the campaign configuration after publishing. Do not attribute aggregate movement when that record is absent.

## Measurement

Success signal: Three accepted-after-adjustment reports from three distinct submitters, at least 20 rolling GitHub unique visitors, and at least five incremental MCPB downloads.

```bash
GH_TOKEN="$(gh auth token)" uv run python scripts/export_campaign_activation_report.py --config docs/campaigns/classification-robustness-2026-08.json --output /tmp/classification-activation.md
```
