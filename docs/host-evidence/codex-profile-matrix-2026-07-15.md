# Codex Capability Profile Acceptance Receipt - 2026-07-15

## Scope

This receipt records a real Codex CLI host session against the unreleased capability-profile implementation. It covers
the `core`, `review`, `dataset`, and `full` server surfaces plus the resource-blind `get_workflow_example` path. It does
not claim a preview workflow, external beta feedback, or adoption evidence.

## Environment

- Host: Codex CLI `0.144.2`
- Host session: `019f65fd-3a77-72a3-ad49-d80d1c753742`
- Runtime source revision: `ffcb3574673d2edae5f4023168f6f3a6a7007795`
- Acceptance packet approval fix: `b4529ef`
- Transport: four temporary local stdio servers from the same prepared checkout
- Host sandbox: read-only
- Persistent host configuration changes: none

The temporary Codex configuration approved only `get_workflow_example` and `run_host_smoke_check`. Rendering,
feedback, cleanup, and export tools retained their normal host approval behavior.

## Observed Matrix

| Profile | Fallback call | Smoke call | Preview ready | Observation |
| --- | --- | --- | --- | --- |
| `core` | passed | passed | `false` | Expected non-preview profile; the preview request template remained gated. |
| `review` | passed | passed | `true` | Preview and feedback profile initialized successfully. |
| `dataset` | passed | passed | `true` | Dataset onboarding and bounded preview profile initialized successfully. |
| `full` | passed | passed | `true` | Canonical v1.x profile initialized successfully. |

The host made eight successful MCP tool calls. For every profile it called
`get_workflow_example(example_id="client-smoke")` and then
`run_host_smoke_check(include_write_probe=false)`. No profile returned a tool error, and the final host result contained
an empty failure list.

## Resource Fallback

The session intentionally exercised the tool fallback instead of depending on a model-visible resource reader. All
four `get_workflow_example` calls completed and returned profile-aware client-smoke guidance. Separate current-source
stdio conformance proved that each fallback payload equals its canonical
`albumentationsx://examples/client-smoke` resource payload.

## Host Policy Finding

An initial non-interactive run discovered all four servers but Codex cancelled MCP calls when no MCP-tool approval mode
was configured. A minimal probe confirmed that explicit approval resolves the host-policy gate. The final packet uses
per-tool `approval_mode="approve"` for the two read-only matrix tools instead of trusting the complete MCP server.

This is a Codex execution-policy behavior, not an AlbumentationsX MCP startup or protocol failure. The accepted packet
configuration keeps broader operations interactive.

## Machine Proof

The companion [profile conformance report](profile-conformance-2026-07-15.json) passed exact ordered surface checks,
smoke semantics, and resource/fallback parity for all four profiles. That report is machine proof only and is not used
as a substitute for this host observation.

## Privacy And Claim Boundary

No raw session transcript, private image, account data, credentials, absolute user path, or host log is committed. The
receipt supports Codex capability-profile and fallback acceptance only. Claude Desktop profile acceptance and its
reviewer-observed `render -> reject -> adjust -> accept` loop remain separate pending work.
