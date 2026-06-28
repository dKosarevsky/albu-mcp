# Product Iteration Governor

Governor status: `sequenced_not_auto_executed`
Iteration count: `100`

## Execution Policy

Each iteration needs a named goal, tests, readiness checks, and evidence gates before merge.
No blind 100-iteration implementation loop is allowed.

## Required Checks

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check`
- `uv run python scripts/check_release_readiness.py`

## Iteration Queue

| Iteration | Lane | Status | Goal |
| --- | --- | --- | --- |
| 1 | `evidence` | `current_priority` | Close P0 real-host evidence for Codex and Claude Code. |
| 2 | `release` | `blocked_until_previous_iteration` | Open the RC gate only after P0 and beta evidence pass. |
| 3 | `beta` | `blocked_until_previous_iteration` | Collect one privacy-safe beta attempt for every workflow. |
| 4 | `product` | `blocked_until_previous_iteration` | Implement the first policy assistant slice after gates open. |
| 5 | `distribution` | `blocked_until_previous_iteration` | Prepare post-RC distribution and registry follow-up. |
| 6 | `quality` | `blocked_until_previous_iteration` | Run product iteration 6 in the quality lane with tests, evidence, and readiness checks. |
| 7 | `docs` | `blocked_until_previous_iteration` | Run product iteration 7 in the docs lane with tests, evidence, and readiness checks. |
| 8 | `adoption` | `blocked_until_previous_iteration` | Run product iteration 8 in the adoption lane with tests, evidence, and readiness checks. |
| 9 | `evidence` | `blocked_until_previous_iteration` | Run product iteration 9 in the evidence lane with tests, evidence, and readiness checks. |
| 10 | `release` | `blocked_until_previous_iteration` | Run product iteration 10 in the release lane with tests, evidence, and readiness checks. |
| 11 | `beta` | `blocked_until_previous_iteration` | Run product iteration 11 in the beta lane with tests, evidence, and readiness checks. |
| 12 | `product` | `blocked_until_previous_iteration` | Run product iteration 12 in the product lane with tests, evidence, and readiness checks. |
| 13 | `distribution` | `blocked_until_previous_iteration` | Run product iteration 13 in the distribution lane with tests, evidence, and readiness checks. |
| 14 | `quality` | `blocked_until_previous_iteration` | Run product iteration 14 in the quality lane with tests, evidence, and readiness checks. |
| 15 | `docs` | `blocked_until_previous_iteration` | Run product iteration 15 in the docs lane with tests, evidence, and readiness checks. |
| 16 | `adoption` | `blocked_until_previous_iteration` | Run product iteration 16 in the adoption lane with tests, evidence, and readiness checks. |
| 17 | `evidence` | `blocked_until_previous_iteration` | Run product iteration 17 in the evidence lane with tests, evidence, and readiness checks. |
| 18 | `release` | `blocked_until_previous_iteration` | Run product iteration 18 in the release lane with tests, evidence, and readiness checks. |
| 19 | `beta` | `blocked_until_previous_iteration` | Run product iteration 19 in the beta lane with tests, evidence, and readiness checks. |
| 20 | `product` | `blocked_until_previous_iteration` | Run product iteration 20 in the product lane with tests, evidence, and readiness checks. |
| 21 | `distribution` | `blocked_until_previous_iteration` | Run product iteration 21 in the distribution lane with tests, evidence, and readiness checks. |
| 22 | `quality` | `blocked_until_previous_iteration` | Run product iteration 22 in the quality lane with tests, evidence, and readiness checks. |
| 23 | `docs` | `blocked_until_previous_iteration` | Run product iteration 23 in the docs lane with tests, evidence, and readiness checks. |
| 24 | `adoption` | `blocked_until_previous_iteration` | Run product iteration 24 in the adoption lane with tests, evidence, and readiness checks. |
| 25 | `evidence` | `blocked_until_previous_iteration` | Run product iteration 25 in the evidence lane with tests, evidence, and readiness checks. |
| 26 | `release` | `blocked_until_previous_iteration` | Run product iteration 26 in the release lane with tests, evidence, and readiness checks. |
| 27 | `beta` | `blocked_until_previous_iteration` | Run product iteration 27 in the beta lane with tests, evidence, and readiness checks. |
| 28 | `product` | `blocked_until_previous_iteration` | Run product iteration 28 in the product lane with tests, evidence, and readiness checks. |
| 29 | `distribution` | `blocked_until_previous_iteration` | Run product iteration 29 in the distribution lane with tests, evidence, and readiness checks. |
| 30 | `quality` | `blocked_until_previous_iteration` | Run product iteration 30 in the quality lane with tests, evidence, and readiness checks. |
| 31 | `docs` | `blocked_until_previous_iteration` | Run product iteration 31 in the docs lane with tests, evidence, and readiness checks. |
| 32 | `adoption` | `blocked_until_previous_iteration` | Run product iteration 32 in the adoption lane with tests, evidence, and readiness checks. |
| 33 | `evidence` | `blocked_until_previous_iteration` | Run product iteration 33 in the evidence lane with tests, evidence, and readiness checks. |
| 34 | `release` | `blocked_until_previous_iteration` | Run product iteration 34 in the release lane with tests, evidence, and readiness checks. |
| 35 | `beta` | `blocked_until_previous_iteration` | Run product iteration 35 in the beta lane with tests, evidence, and readiness checks. |
| 36 | `product` | `blocked_until_previous_iteration` | Run product iteration 36 in the product lane with tests, evidence, and readiness checks. |
| 37 | `distribution` | `blocked_until_previous_iteration` | Run product iteration 37 in the distribution lane with tests, evidence, and readiness checks. |
| 38 | `quality` | `blocked_until_previous_iteration` | Run product iteration 38 in the quality lane with tests, evidence, and readiness checks. |
| 39 | `docs` | `blocked_until_previous_iteration` | Run product iteration 39 in the docs lane with tests, evidence, and readiness checks. |
| 40 | `adoption` | `blocked_until_previous_iteration` | Run product iteration 40 in the adoption lane with tests, evidence, and readiness checks. |
| 41 | `evidence` | `blocked_until_previous_iteration` | Run product iteration 41 in the evidence lane with tests, evidence, and readiness checks. |
| 42 | `release` | `blocked_until_previous_iteration` | Run product iteration 42 in the release lane with tests, evidence, and readiness checks. |
| 43 | `beta` | `blocked_until_previous_iteration` | Run product iteration 43 in the beta lane with tests, evidence, and readiness checks. |
| 44 | `product` | `blocked_until_previous_iteration` | Run product iteration 44 in the product lane with tests, evidence, and readiness checks. |
| 45 | `distribution` | `blocked_until_previous_iteration` | Run product iteration 45 in the distribution lane with tests, evidence, and readiness checks. |
| 46 | `quality` | `blocked_until_previous_iteration` | Run product iteration 46 in the quality lane with tests, evidence, and readiness checks. |
| 47 | `docs` | `blocked_until_previous_iteration` | Run product iteration 47 in the docs lane with tests, evidence, and readiness checks. |
| 48 | `adoption` | `blocked_until_previous_iteration` | Run product iteration 48 in the adoption lane with tests, evidence, and readiness checks. |
| 49 | `evidence` | `blocked_until_previous_iteration` | Run product iteration 49 in the evidence lane with tests, evidence, and readiness checks. |
| 50 | `release` | `blocked_until_previous_iteration` | Run product iteration 50 in the release lane with tests, evidence, and readiness checks. |
| 51 | `beta` | `blocked_until_previous_iteration` | Run product iteration 51 in the beta lane with tests, evidence, and readiness checks. |
| 52 | `product` | `blocked_until_previous_iteration` | Run product iteration 52 in the product lane with tests, evidence, and readiness checks. |
| 53 | `distribution` | `blocked_until_previous_iteration` | Run product iteration 53 in the distribution lane with tests, evidence, and readiness checks. |
| 54 | `quality` | `blocked_until_previous_iteration` | Run product iteration 54 in the quality lane with tests, evidence, and readiness checks. |
| 55 | `docs` | `blocked_until_previous_iteration` | Run product iteration 55 in the docs lane with tests, evidence, and readiness checks. |
| 56 | `adoption` | `blocked_until_previous_iteration` | Run product iteration 56 in the adoption lane with tests, evidence, and readiness checks. |
| 57 | `evidence` | `blocked_until_previous_iteration` | Run product iteration 57 in the evidence lane with tests, evidence, and readiness checks. |
| 58 | `release` | `blocked_until_previous_iteration` | Run product iteration 58 in the release lane with tests, evidence, and readiness checks. |
| 59 | `beta` | `blocked_until_previous_iteration` | Run product iteration 59 in the beta lane with tests, evidence, and readiness checks. |
| 60 | `product` | `blocked_until_previous_iteration` | Run product iteration 60 in the product lane with tests, evidence, and readiness checks. |
| 61 | `distribution` | `blocked_until_previous_iteration` | Run product iteration 61 in the distribution lane with tests, evidence, and readiness checks. |
| 62 | `quality` | `blocked_until_previous_iteration` | Run product iteration 62 in the quality lane with tests, evidence, and readiness checks. |
| 63 | `docs` | `blocked_until_previous_iteration` | Run product iteration 63 in the docs lane with tests, evidence, and readiness checks. |
| 64 | `adoption` | `blocked_until_previous_iteration` | Run product iteration 64 in the adoption lane with tests, evidence, and readiness checks. |
| 65 | `evidence` | `blocked_until_previous_iteration` | Run product iteration 65 in the evidence lane with tests, evidence, and readiness checks. |
| 66 | `release` | `blocked_until_previous_iteration` | Run product iteration 66 in the release lane with tests, evidence, and readiness checks. |
| 67 | `beta` | `blocked_until_previous_iteration` | Run product iteration 67 in the beta lane with tests, evidence, and readiness checks. |
| 68 | `product` | `blocked_until_previous_iteration` | Run product iteration 68 in the product lane with tests, evidence, and readiness checks. |
| 69 | `distribution` | `blocked_until_previous_iteration` | Run product iteration 69 in the distribution lane with tests, evidence, and readiness checks. |
| 70 | `quality` | `blocked_until_previous_iteration` | Run product iteration 70 in the quality lane with tests, evidence, and readiness checks. |
| 71 | `docs` | `blocked_until_previous_iteration` | Run product iteration 71 in the docs lane with tests, evidence, and readiness checks. |
| 72 | `adoption` | `blocked_until_previous_iteration` | Run product iteration 72 in the adoption lane with tests, evidence, and readiness checks. |
| 73 | `evidence` | `blocked_until_previous_iteration` | Run product iteration 73 in the evidence lane with tests, evidence, and readiness checks. |
| 74 | `release` | `blocked_until_previous_iteration` | Run product iteration 74 in the release lane with tests, evidence, and readiness checks. |
| 75 | `beta` | `blocked_until_previous_iteration` | Run product iteration 75 in the beta lane with tests, evidence, and readiness checks. |
| 76 | `product` | `blocked_until_previous_iteration` | Run product iteration 76 in the product lane with tests, evidence, and readiness checks. |
| 77 | `distribution` | `blocked_until_previous_iteration` | Run product iteration 77 in the distribution lane with tests, evidence, and readiness checks. |
| 78 | `quality` | `blocked_until_previous_iteration` | Run product iteration 78 in the quality lane with tests, evidence, and readiness checks. |
| 79 | `docs` | `blocked_until_previous_iteration` | Run product iteration 79 in the docs lane with tests, evidence, and readiness checks. |
| 80 | `adoption` | `blocked_until_previous_iteration` | Run product iteration 80 in the adoption lane with tests, evidence, and readiness checks. |
| 81 | `evidence` | `blocked_until_previous_iteration` | Run product iteration 81 in the evidence lane with tests, evidence, and readiness checks. |
| 82 | `release` | `blocked_until_previous_iteration` | Run product iteration 82 in the release lane with tests, evidence, and readiness checks. |
| 83 | `beta` | `blocked_until_previous_iteration` | Run product iteration 83 in the beta lane with tests, evidence, and readiness checks. |
| 84 | `product` | `blocked_until_previous_iteration` | Run product iteration 84 in the product lane with tests, evidence, and readiness checks. |
| 85 | `distribution` | `blocked_until_previous_iteration` | Run product iteration 85 in the distribution lane with tests, evidence, and readiness checks. |
| 86 | `quality` | `blocked_until_previous_iteration` | Run product iteration 86 in the quality lane with tests, evidence, and readiness checks. |
| 87 | `docs` | `blocked_until_previous_iteration` | Run product iteration 87 in the docs lane with tests, evidence, and readiness checks. |
| 88 | `adoption` | `blocked_until_previous_iteration` | Run product iteration 88 in the adoption lane with tests, evidence, and readiness checks. |
| 89 | `evidence` | `blocked_until_previous_iteration` | Run product iteration 89 in the evidence lane with tests, evidence, and readiness checks. |
| 90 | `release` | `blocked_until_previous_iteration` | Run product iteration 90 in the release lane with tests, evidence, and readiness checks. |
| 91 | `beta` | `blocked_until_previous_iteration` | Run product iteration 91 in the beta lane with tests, evidence, and readiness checks. |
| 92 | `product` | `blocked_until_previous_iteration` | Run product iteration 92 in the product lane with tests, evidence, and readiness checks. |
| 93 | `distribution` | `blocked_until_previous_iteration` | Run product iteration 93 in the distribution lane with tests, evidence, and readiness checks. |
| 94 | `quality` | `blocked_until_previous_iteration` | Run product iteration 94 in the quality lane with tests, evidence, and readiness checks. |
| 95 | `docs` | `blocked_until_previous_iteration` | Run product iteration 95 in the docs lane with tests, evidence, and readiness checks. |
| 96 | `adoption` | `blocked_until_previous_iteration` | Run product iteration 96 in the adoption lane with tests, evidence, and readiness checks. |
| 97 | `evidence` | `blocked_until_previous_iteration` | Run product iteration 97 in the evidence lane with tests, evidence, and readiness checks. |
| 98 | `release` | `blocked_until_previous_iteration` | Run product iteration 98 in the release lane with tests, evidence, and readiness checks. |
| 99 | `beta` | `blocked_until_previous_iteration` | Run product iteration 99 in the beta lane with tests, evidence, and readiness checks. |
| 100 | `product` | `blocked_until_previous_iteration` | Run product iteration 100 in the product lane with tests, evidence, and readiness checks. |

## Source Docs

- `docs/REAL_HOST_EVIDENCE_COMMAND_CENTER.md`
- `docs/RC_EVIDENCE_REOPEN_FLOW.md`
- `docs/BETA_VALIDATION_LOOP.md`
- `docs/POLICY_ASSISTANT_PLAN.md`
