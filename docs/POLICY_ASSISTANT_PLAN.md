# Policy Assistant Plan

Plan status: `blocked_until_rc_and_beta_signal`
Implementation allowed: `false`
First slice: `feedback_aware_policy_recommendation`

## Product Thesis

Turn AlbumentationsX MCP into an interactive augmentation-policy assistant.

## Blocked Reasons

- `p0_host_evidence_missing_or_blocked`
- `beta_validation_records_missing`

## Components

| Component | Responsibility | Depends On |
| --- | --- | --- |
| `dataset_signal_reader` | Summarize dataset task, sample count, annotations, and preview constraints. | existing dataset onboarding and quality inspection reports |
| `policy_candidate_generator` | Propose bounded AlbumentationsX policy candidates with explicit risk notes. | recipe catalog, transform schemas, and beta validation findings |
| `preview_feedback_loop` | Map user feedback like too noisy or object lost into safer next candidates. | preview comparison, feedback interpretation, and tuning decision records |
| `exportable_policy_contract` | Export accepted policy as reproducible Python/YAML plus a short review report. | existing export pipeline and output contract snapshots |

## Acceptance Gates

- P0 real-host evidence passed for Codex and Claude Code.
- Every beta validation workflow has a privacy-safe real attempt.
- First slice has failing tests before runtime behavior changes.
- Output contracts are regenerated only after reviewed behavior changes.

## Next Actions

- Do not start runtime implementation until RC and beta gates open.
- Use this plan to prepare tests and API boundaries only.
- Rebuild the plan after real host and beta evidence changes.

## Source Docs

- `docs/PRODUCT_DEPTH_SELECTION.md`
- `docs/BETA_TO_BACKLOG_TRIAGE.md`
- `docs/BETA_VALIDATION_LOOP.md`
- `docs/V1_RC_CUTOVER_GATE.md`
