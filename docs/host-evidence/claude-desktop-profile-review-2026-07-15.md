# Claude Desktop Capability Profile Receipt - 2026-07-15

## Scope

This receipt records a real Claude Desktop startup against the unreleased capability-profile implementation. It
separates observed MCP initialization from model-driven profile acceptance and the reviewer-observed
`render -> reject -> adjust -> accept` workflow. The latter two were blocked by the host service before any tool call
could run.

## Environment

- Host: Claude Desktop `1.21459.0`
- Source revision: `b24f8ff52b4af13b6e1cb2803949d449642dd2d6`
- Transport: four temporary local stdio servers from the same prepared checkout
- Profiles: `core`, `review`, `dataset`, and `full`
- Input: repository-generated sample fixture
- Persistent host configuration changes: none after cleanup

The temporary configuration was merged structurally with the existing Claude Desktop configuration. Unrelated
top-level settings were preserved, and a pre-run backup was retained until cleanup completed.

## Observed Initialization

| Profile | Server connected | Tool discovery requested | Resource discovery requested | Model tool calls |
| --- | --- | --- | --- | --- |
| `core` | passed | observed | observed | none |
| `review` | passed | observed | observed | none |
| `dataset` | passed | observed | observed | none |
| `full` | passed | observed | observed | none |

Claude Desktop started all four exact-current-source processes. Each server completed MCP initialization and received
the host's `tools/list` and `resources/list` requests. This proves host-side server loading and surface discovery; it
does not prove model visibility or tool execution.

## Host Service Blocker

The Claude renderer was redirected to Anthropic's public `app-unavailable-in-region` endpoint. Subsequent host API
requests failed before a usable conversation editor or model turn became available. The profile prompt therefore
produced no `tools/call` or `resources/read` request in any server log.

This is an external Claude service availability condition. It is not classified as an AlbumentationsX MCP startup,
transport, capability-profile, or protocol failure.

## Acceptance Status

- Profile matrix: **blocked before model execution**
- Direct resource path: **not observed**
- Resource-blind `get_workflow_example` fallback: **not observed in Claude Desktop**
- Smoke calls: **not observed in Claude Desktop**
- Reviewer-observed feedback loop: **not run**
- Preview artifacts: **none generated**

The companion Codex receipt and stdio conformance report cover real fallback calls and exact resource/fallback parity,
respectively. They are not used as substitutes for the missing Claude Desktop observations.

## Rerun Gate

When Claude Desktop can reach the Claude service from a supported network location, regenerate the packet from the
then-current revision and repeat both prompts. A passing replacement receipt requires:

1. one model-driven fallback or resource read plus smoke call for every profile;
2. a baseline preview inspected and explicitly rejected by a reviewer;
3. an adjusted candidate inspected and explicitly accepted by a reviewer;
4. verified manifests and image hashes under the bounded artifact root.

## Privacy And Claim Boundary

No raw conversation, account or organization identifier, credential, absolute user path, private image, or host log
is committed. This receipt supports Claude Desktop initialization evidence only. It makes no workflow-completion,
beta-feedback, adoption, or campaign claim.
