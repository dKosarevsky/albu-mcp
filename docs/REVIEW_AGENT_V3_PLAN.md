# Review Agent V3 Plan

Plan status: `waiting_for_beta_signal`
Triage bucket: `review_agent_v3_gap`
Product area: `preview_review_agent`
Priority: `p1_after_p0`
Beta record count: `0`

## Candidate

Feedback-to-adjustment planning that better handles noisy or unreadable previews.

## Success Signal

Repeated noisy-preview feedback maps to safer candidate adjustments.

## Tracks

| Track | Scope | Test Seed |
| --- | --- | --- |
| `feedback_intent_calibration` | Map free-form feedback to stable tags, intents, and severity. | Add beta-derived cases to tests/test_review_agent.py. |
| `safe_adjustment_planning` | Recommend safer adjustment steps for noisy or unreadable candidates. | Assert destructive transforms are reduced before adding new transforms. |
| `object_readability_guard` | Protect object readability when feedback says the object is unrecognizable. | Add regression cases for object_unrecognizable feedback. |

## Implementation Guards

- Do not change runtime review behavior without repeated beta feedback or a failing test.
- Preserve existing review_agent output fields and contract snapshots.
- Keep the first implementation behind tests before updating public docs.

## Acceptance Gates

- At least one repeated review_agent_v3_gap record exists or a maintainer supplies a concrete failing case.
- New tests fail before implementation and pass after implementation.
- Golden MCP evals and output contract snapshots remain stable or are intentionally updated.

## Source Docs

- `docs/BETA_FEEDBACK_STATUS.md`
- `docs/PRODUCT_DEPTH_BACKLOG.md`
- `docs/BETA_VALIDATION_SPRINT.md`
