# Dataset-Aware Onboarding Design

## Goal

Extend `plan_dataset_onboarding` from a safe image sampler into a dataset-aware first-preview planner. The tool should
recognize common local dataset layouts and return agent-legible hints without mutating files, rendering previews, or
performing expensive full-dataset analysis.

## Scope

This increment adds read-only profile detection for:

- image classification class-directory layouts such as `cats/*.jpg` and `dogs/*.jpg`;
- split folders such as `train`, `val`, `valid`, and `test`;
- YOLO label sidecars under `labels/**/*.txt`;
- COCO annotation manifests such as `annotations/instances_train.json`.

The output remains part of `DatasetOnboardingReport`. Existing fields keep their meaning. New profile fields describe
detected layout signals, annotation format signals, class balance hints, and recipe hints. The preview request template
still uses only local image paths and the recommended pipeline.

## Architecture

Keep filesystem inventory and dataset profiling separate. `onboarding.py` continues to own the public report builder, but
dataset structure detection moves into a focused helper module so future COCO/YOLO parsing can grow independently.

The helper receives already validated local roots and image paths. It never opens image bytes and only reads small text or
JSON metadata when needed for format detection. It returns strict Pydantic models that can be serialized directly through
the MCP tool.

## Data Model

Add `DatasetStructureProfile` to the onboarding report with these fields:

- `detected_layouts`: stable string codes such as `class_directories`, `split_directories`, `yolo_labels`, `coco_manifest`;
- `class_directories`: class folder names and image counts for likely classification datasets;
- `splits`: split names and image counts;
- `annotation_formats`: detected annotation formats and representative files;
- `balance_warnings`: human-readable warnings for obvious class imbalance;
- `recipe_hints`: concise next-step hints for host agents.

## Error Handling

Profiling is best-effort. Unsupported or malformed annotation files should produce warning hints, not block preview
planning. Existing hard failures remain path-policy, missing path, non-directory path, empty image inventory, and invalid
recommended pipeline.

## Testing

Use TDD:

1. Add failing unit tests for class-directory and split detection.
2. Add failing unit tests for YOLO and COCO format detection.
3. Add a failing contract/export test that expects `dataset_structure` in the output snapshot.
4. Implement the smallest profile helper and wire it into `build_dataset_onboarding_report`.
5. Update docs, snapshots, and golden eval expectations.

## Non-Goals

Do not parse every annotation object, compute image dimensions, validate bbox geometry, train models, or recommend
dataset curation changes beyond obvious first-preview hints.
