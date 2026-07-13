# Claude Desktop Host Acceptance Design

## Goal

Close the first real Claude Desktop MCPB acceptance loop and make the first-run smoke workflow reliable in hosts that
discover MCP resources but do not expose resource reads directly to the model.

## Observed Host Behavior

Claude Desktop Free installed the local `albumentationsx-mcp` MCPB, created its UV environment, saved explicit read and
artifact roots, initialized the server, and completed `tools/list`, `prompts/list`, and `resources/list`. A real
`tools/call` to `run_host_smoke_check` returned `preview_ready=true` with no MCP error.

The model reported that it could not directly read `albumentationsx://examples/client-smoke`, even though the host had
successfully listed the resource. This is a host capability difference, not a server discovery failure. Critical safety
guidance therefore cannot depend on model-visible resource retrieval.

## Chosen Approach

Keep MCP Resources as the canonical detailed playbooks, but make them optional accelerators:

- expand the `run_host_smoke_check` tool description so discovery tells models they may call it directly;
- add typed workflow guidance to `HostSmokeReport`, including the optional resource URI, the preview gate, and the safe
  validation/render sequence;
- retain `next_actions` and the bounded preview request template as the authoritative task-specific handoff;
- update first-run prompts, skills, and concise installation/usage documentation to describe both host paths.

No resource proxy tool will be added. That would duplicate the MCP protocol, increase the public tool surface, and
create two sources of truth for the same playbook.

## Architecture

`host_smoke.py` owns the host-neutral typed response. `server.py` remains a thin FastMCP adapter whose docstring exposes
the fallback during `tools/list`. Prompt and skill text consume the same policy but do not implement product logic. The
MCPB wrapper continues to delegate directly to the matching published package.

## Acceptance Evidence

Add a sanitized Claude Desktop receipt that distinguishes:

- real host evidence: installation, configuration, initialization, discovery, and successful smoke tool invocation;
- generated-fixture evidence: a bounded preview rendered from the dedicated local fixture;
- unproven claims: external beta use, adoption, or real user dataset quality.

The receipt must not contain account identifiers, raw chat transcripts, credentials, or private absolute dataset paths.
The existing blocked Claude Code record remains unchanged.

## Testing

- Unit tests require the smoke report to declare resource retrieval optional and return the safe ordered workflow.
- MCP server tests require the tool description to explain the direct-call fallback.
- Skill and documentation tests require optional-resource wording.
- The installed MCPB must render one bounded generated-fixture preview under its configured roots.
- Full pytest, Ruff, formatting, ty, contract snapshots, golden evals, desktop-extension validation, and release readiness
  remain release gates.

## Release

Prepare `v1.17.0` because the release introduces a new distributable MCPB and a backward-compatible public smoke-report
field. The GitHub release attaches the MCPB and checksum; PyPI and MCP Registry continue through the existing trusted
release workflow.

## Non-Goals

- Adding a generic MCP resource reader tool.
- Treating generated fixture output as beta or adoption evidence.
- Marking Claude Code as passed.
- Expanding filesystem permissions or exposing a remote MCP endpoint.
