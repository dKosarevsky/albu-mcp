# Policy Assistant MVP Contract

Contract status: `blocked_until_rc_and_beta_signal`
Runtime implementation allowed: `false`
Safe runtime MVP available: `true`
Production policy acceptance allowed: `false`
First slice: `feedback_aware_policy_recommendation`

## Contract Policy

Safe runtime MVP behavior may produce starter candidates only. It does not open product-depth, RC, beta, export, or production policy acceptance gates without real preview and host evidence.

## Blocked Reasons

- `p0_host_evidence_missing_or_blocked`
- `beta_validation_records_missing`

## Interfaces

| Interface | Fields | Purpose |
| --- | --- | --- |
| `policy_context` | `task`, `sample_count`, `annotation_type`, `preview_constraints` | Carry dataset and review context into recommendation planning. |
| `feedback_signal` | `tag`, `severity`, `freeform_note`, `rejected_candidate_id` | Normalize user feedback such as too_noisy or object_lost. |
| `recommendation_result` | `candidate_pipeline`, `risk_notes`, `next_preview_request`, `export_hint` | Describe the next safe policy candidate without mutating files. |

## Golden Scenarios

- `too_noisy_high_reduces_noise_strength`
- `object_lost_reduces_geometric_distortion`
- `looks_good_preserves_exportable_pipeline`

## Source Docs

- `docs/POLICY_ASSISTANT_PLAN.md`
- `docs/POLICY_ASSISTANT_MVP_CONTRACT.md`
- `docs/PRODUCT_DEPTH_SELECTION.md`
- `docs/BETA_TO_BACKLOG_TRIAGE.md`
