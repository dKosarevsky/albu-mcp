# Dataset Quality Depth Plan

Plan status: `waiting_for_beta_signal`
Triage bucket: `dataset_quality_gap`
Product area: `dataset_quality`
Priority: `p1_after_p0`
Beta record count: `0`

## Candidate

Deeper dataset health findings for annotations, class balance, and duplicate handling.

## Success Signal

Dataset issues are caught before preview rendering in beta workflows.

## Tracks

| Track | Scope | Test Seed |
| --- | --- | --- |
| `annotation_consistency_depth` | Deepen COCO/YOLO/class-directory annotation consistency findings. | Add beta-derived missing/orphan/out-of-bounds annotation fixtures. |
| `bbox_mask_preview_readiness` | Expose whether bbox and mask datasets are safe to preview before augmentation. | Assert blockers are reported before render_preview_batch is suggested. |
| `duplicate_and_split_risk` | Improve duplicate, class imbalance, and split imbalance prioritization. | Add fixtures that distinguish warning-only from render-blocking findings. |

## Implementation Guards

- Do not change runtime dataset-quality behavior without repeated beta feedback or a failing test.
- Keep dataset inspection read-only and bounded by allowed roots.
- Preserve existing output contract snapshots unless a public contract change is intentional.

## Acceptance Gates

- At least one repeated dataset_quality_gap record exists or a maintainer supplies a concrete failing case.
- New tests fail before implementation and pass after implementation.
- Preview rendering remains blocked only for high-confidence path or annotation safety issues.

## Source Docs

- `docs/BETA_FEEDBACK_STATUS.md`
- `docs/PRODUCT_DEPTH_BACKLOG.md`
- `docs/BETA_VALIDATION_SPRINT.md`
