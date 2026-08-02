# MCP 2026-07-28 Compatibility Design

## Context

AlbumentationsX MCP 1.20.0 is pinned to MCP Python SDK 1.x. MCP `2026-07-28` makes the core HTTP protocol stateless,
adds `server/discover`, typed results, cache hints, trace context, and an extension model. The Python SDK 2.0 release
implements the new protocol while retaining legacy protocol negotiation, but it replaces `FastMCP` with `MCPServer`
and introduces a new client and MCP Apps API.

The server already uses explicit application identifiers such as `run_id`, `feedback_id`, and artifact URIs. Those
identifiers remain application state and must not be confused with removed transport sessions.

## Decision

Migrate to MCP Python SDK `>=2.0.0,<3` and support both protocol eras from one server:

- modern clients negotiate MCP `2026-07-28` and use `server/discover`;
- legacy clients continue to use `initialize` and the existing session behavior provided by the SDK;
- the package name, `albumentationsx-mcp` command, stdio default, optional Streamable HTTP transport, capability
  profiles, and every public tool/resource/prompt name and schema remain compatible;
- SDK-generated protocol envelopes, including `resultType`, cache fields, and trace context, are not duplicated in
  application code;
- MCP Apps metadata and HTML resources move to the official SDK extension API.

The migration changes the concrete object returned by `create_mcp_server` from SDK v1 `FastMCP` to SDK v2
`MCPServer`. The function path, arguments, runtime behavior, and supported embedding workflow remain stable. This is
the only source-level compatibility caveat for callers that inspect SDK-private internals.

## Architecture

### SDK Boundary

Application and domain services remain independent of MCP. MCP adapters target a local `McpRegistrar` protocol
instead of importing an upstream server class. `server.py` is the composition root that creates `MCPServer`, SDK
extensions, adapter dependencies, and transport configuration.

Profile filtering is performed by a registrar decorator proxy. It delegates only declarations selected by the
validated capability profile. This removes reads and writes to SDK-private tool, resource, template, and prompt
manager dictionaries.

### MCP Apps

The preview review UI is assembled as an official `Apps` extension before `MCPServer` construction. The extension
owns the preview render tools and `ui://albumentationsx/preview-review` HTML resource. The remaining preview adapter
owns artifact resources and feedback tools. The externally visible names, schemas, metadata, and profile availability
stay unchanged.

### Protocol Compatibility

The SDK owns modern discovery, legacy initialization, result envelopes, and transport negotiation. Integration tests
connect through the public SDK client in both `2026-07-28` and `legacy` modes and assert the same canonical surface.
At least one representative tool call and resource read run in both modes.

Static contract export uses public asynchronous server listing APIs. It continues to compare against the existing
snapshot, proving that the migration does not alter the product contract.

### State And Long Operations

Application state continues to use explicit IDs and artifact paths. No protocol session is used as an application
identifier. MCP Tasks are deliberately deferred: Python SDK 2.0 does not yet expose the final Tasks extension, so a
project-specific emulation would create a non-standard contract. Existing bounded synchronous operations and progress
reporting remain unchanged until official SDK support is available.

## Compatibility Contract

The following are release gates:

- all 47 tools, 21 resources, two resource templates, and five prompts remain present in the full profile;
- profile-specific subsets remain unchanged;
- existing JSON input schemas and structured result payloads remain compatible;
- existing stdio and Streamable HTTP launch commands remain valid;
- legacy and modern clients can discover and invoke the server;
- the preview MCP App remains usable by extension-aware hosts and remains harmless metadata for older hosts.

## Verification

- parameterized modern/legacy protocol tests;
- exact MCP contract snapshot and capability-profile tests;
- official Apps metadata, resource, and invocation tests;
- CLI and host-conformance smoke checks migrated to the public SDK v2 client;
- full pytest, Ruff, formatting, ty, golden evaluations, package build, and release-readiness checks.

## Delivery

Implement the migration as a compatibility candidate on a feature branch. Do not publish a release from this change
without a separate release decision. Document the supported protocol eras and the concrete embedding caveat in the
changelog and compatibility guide.

## Non-Goals

- Removing legacy protocol support.
- Adding remote hosting, OAuth, subscriptions, or application-level persistence.
- Implementing MCP Tasks before official Python SDK support exists.
- Changing augmentation behavior or adding new product tools as part of the protocol migration.
