# Claude Desktop Capability Profile Receipt - 2026-07-15

## Scope

This receipt records two real Claude Desktop attempts against the unreleased capability-profile implementation. It
separates observed MCP initialization, server-side tool completion, model-visible output, and the reviewer-observed
`render -> reject -> adjust -> accept` workflow. Partial execution is not promoted to profile acceptance.

## Environment

- Host: Claude Desktop `1.21459.0`, Free-plan Chat
- Source revision for the completed tool calls: `958ed0cfb5c91366722ca25fb71909c3698ddec8`
- Transport: four temporary local stdio servers from the same prepared checkout
- Profiles: `core`, `review`, `dataset`, and `full`
- Input: repository-generated sample fixture
- Persistent host configuration changes: none after cleanup

The temporary configuration was merged structurally with the existing Claude Desktop configuration. Unrelated
top-level settings were preserved, and a pre-run backup was retained until cleanup completed.

## Observed Initialization

| Profile | Server connected | Tool discovery | Resource discovery | Model-driven tool calls |
| --- | --- | --- | --- | --- |
| `core` | passed | observed | observed | two server responses; first rendered, second lost by host bridge |
| `review` | passed | observed | observed | none |
| `dataset` | passed | observed | observed | none |
| `full` | passed | observed | observed | none |

Claude Desktop started all four exact-current-source processes. Each server completed MCP initialization and received
the host's `tools/list` and `resources/list` requests. This proves host-side server loading and surface discovery; it
does not prove complete model visibility or profile acceptance.

## Partial Core Execution

After the Claude service became reachable, the conversation executed two `core` tool calls. The first call returned in
36 ms and its smoke output was rendered in the conversation. The second call returned one valid MCP content block in
1.48 seconds, but the conversation later displayed a four-minute "No result received from the Claude Desktop app"
error. The next profiles were never called.

The rendered smoke output exposed a product-contract gap: the active profile had to be inferred from remediation text
and the temporary artifact-root suffix. Follow-up revision `c1704df2a4c7c18136e3de95968de8a9fabd2e49` adds an
explicit top-level `capability_profile` field to diagnostics and host smoke output. The companion schema-v2 stdio
conformance report at revision `2d749e42b957d6256b02b76b323ed314a5def368` calls both tools and verifies that field
for all four profiles. It does not replace a real Claude Desktop rerun.

## Host Bridge And Quota Boundary

The local MCP log proves that the server completed both requests before the host error. No server crash, disconnect,
protocol error, or long-running handler was observed. The failed boundary is therefore after the local MCP server and
before the result became available to the Claude conversation.

Claude Desktop then reported that the Free-plan message allowance was exhausted until 23:10 local time. That account
limit prevented a same-session retry and is recorded separately from the host bridge failure.

## Acceptance Status

- Profile matrix: **partial; pending rerun**
- Direct resource path: **not observed**
- Resource-blind `get_workflow_example` fallback: **server response observed for `core`; model-visible result not observed**
- Smoke calls: **model-visible output observed for `core` only**
- `review`, `dataset`, and `full` tool execution: **not run**
- Reviewer-observed feedback loop: **not run**
- Preview artifacts: **none generated**

The companion Codex receipt and stdio conformance report cover real fallback calls and exact resource/fallback parity,
respectively. They are not used as substitutes for the missing Claude Desktop observations.

## Rerun Gate

After the Free-plan allowance resets, restart Claude Desktop on the then-current revision and run one profile per
conversation. A passing replacement receipt requires:

1. an explicitly reported `capability_profile` plus smoke result for every profile;
2. one model-visible fallback result when resource reads are unavailable;
3. a baseline preview inspected and explicitly rejected by a reviewer;
4. an adjusted candidate inspected and explicitly accepted by a reviewer;
5. verified manifests and image hashes under the bounded artifact root.

## Privacy And Claim Boundary

No raw conversation, account or organization identifier, credential, absolute user path, private image, or host log
is committed. This receipt supports Claude Desktop initialization and partial `core` execution evidence only. It makes
no complete profile-workflow, beta-feedback, adoption, or campaign claim.
