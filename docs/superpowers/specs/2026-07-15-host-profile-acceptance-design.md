# Host Profile Acceptance Design

## Goal

Validate the new `core`, `review`, `dataset`, and `full` capability profiles through real Codex and Claude Desktop
hosts, prove the `get_workflow_example` fallback in a resource-blind host, and complete one reviewer-observed Claude
Desktop `render -> reject -> adjust -> accept` loop without misclassifying generated fixtures as adoption evidence.

## Evidence Classes

The validation keeps three evidence classes separate:

1. **Protocol conformance** starts the current checkout over MCP stdio, verifies the exact profile surface, calls the
   smoke tool, and checks resource/fallback parity. It is machine proof only.
2. **Real host acceptance** records what a reviewer observed in Codex or Claude Desktop. A host result is never inferred
   from protocol conformance.
3. **Workflow evidence** records the bounded generated-fixture review loop. It proves host usability and artifact
   handling, but it is not external beta feedback or product adoption.

Every report identifies the source revision, server command, profile, host, date, status, and privacy-safe artifacts.
Templates and unexecuted prompts remain `pending`.

## Scope

### Capability Profile Matrix

Both target hosts must discover four separately named server instances backed by the same current checkout:

| Server | Profile | Required observation |
| --- | --- | --- |
| `albumentationsx_core` | `core` | focused non-preview surface; smoke explains how to select a preview profile |
| `albumentationsx_review` | `review` | preview and feedback surface is available |
| `albumentationsx_dataset` | `dataset` | bounded onboarding, preview, feedback, compare, and report path is available |
| `albumentationsx_full` | `full` | canonical v1.x surface remains available |

The generated configuration uses an explicit Python executable from the prepared environment and absolute bounded
roots. It does not mutate global host configuration automatically.

### Resource Fallback

The host first attempts to read `albumentationsx://examples/client-smoke` when resource reads are exposed to the model.
When that operation is unavailable, it calls `get_workflow_example(example_id="client-smoke")`. The receipt records
which path was observed and verifies that the fallback returns profile-aware smoke and next-step guidance.

### Claude Desktop Review Loop

The `review` profile performs one deterministic generated-fixture flow:

1. run the host smoke check and validate the request;
2. render a deliberately excessive noise baseline;
3. record `too_noisy:high` rejection feedback;
4. call `adjust_pipeline` and render the returned safer candidate;
5. compare baseline and candidate;
6. record an explicit accepted decision only after reviewer inspection.

The receipt may reference sanitized contact sheets, manifests, and exported pipeline/report artifacts. It must not
contain private dataset paths, account information, credentials, or raw chat logs.

## Components

### Profile Acceptance Packet

`scripts/export_host_profile_acceptance_packet.py` creates an operator directory containing:

- `README.md` with evidence classification and execution order;
- `codex-config.toml` and `claude-desktop-config.json` with four isolated profile servers;
- `profile-matrix-prompt.md` for discovery, smoke, and fallback checks;
- `claude-review-loop-prompt.md` for the bounded feedback loop;
- `receipt-template.json` with all observations explicitly pending.

The exporter accepts an explicit server Python executable, source revision, roots, sample image, hosts, and output
directory. It refuses relative paths, missing sample images, roots that do not contain the sample, and artifact roots
inside the read root.

### Machine Conformance Report

`scripts/check_host_profile_conformance.py` launches the same current checkout through the MCP SDK for each profile.
It checks exact tool/resource/prompt membership, calls `run_host_smoke_check`, reads the client-smoke resource, calls
the fallback tool, and verifies payload parity. It emits one deterministic privacy-safe JSON report and exits nonzero
on mismatch.

### Host Receipts

Completed receipts are stored under `docs/host-evidence/` only after reviewer observation. A receipt distinguishes
machine proof, host UI proof, and generated-fixture workflow proof. Existing `docs/HOST_MANUAL_RUNS.json` records are
updated only when an existing manual acceptance kind has actually passed.

## Error Handling

- Unknown profiles or non-absolute paths fail before writing packet files.
- An unavailable server executable, missing sample, or invalid root relation fails with one actionable message.
- A host startup or tool-call failure records the first failing gate as `blocked`; it does not produce a passed receipt.
- Resource-read failure is expected only when fallback succeeds; failure of both paths blocks that profile.
- Partial Claude Desktop execution remains pending and does not alter canonical host evidence.

## Testing

- Unit tests cover packet validation, deterministic host configurations, profile-specific prompts, pending receipt
  defaults, and privacy language.
- Parameterized protocol tests cover all four profiles, exact surfaces, smoke semantics, and resource/fallback parity.
- Focused Ruff and ty checks run before the full suite.
- The real Codex run uses `codex exec --ephemeral` with temporary configuration overrides and no persistent MCP edits.
- Claude Desktop completion requires reviewer-observed UI output and verified generated artifacts.

## Delivery

1. Commit this design and its implementation plan.
2. Add the packet exporter and tests.
3. Add machine conformance and run it against the branch.
4. Execute and record Codex host acceptance.
5. Execute Claude Desktop acceptance, verify artifacts, update evidence, independently review, and merge.

No package version, tag, Registry entry, or release is changed by this iteration.

## Success Criteria

- All four profiles pass exact current-source stdio conformance.
- Real Codex observes all four profiles and successfully uses the client-smoke fallback.
- Real Claude Desktop observes all four profiles and successfully uses the fallback when resource reads are unavailable.
- Claude Desktop completes one reviewer-observed `render -> reject -> adjust -> accept` generated-fixture loop.
- Evidence remains privacy-safe and never claims beta feedback or adoption.
