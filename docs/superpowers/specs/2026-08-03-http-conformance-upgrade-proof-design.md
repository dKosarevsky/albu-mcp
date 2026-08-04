# Streamable HTTP Conformance and Published Upgrade Proof Design

## Context

AlbumentationsX MCP `1.21.0` supports MCP `2026-07-28` and the legacy initialize handshake through MCP Python SDK
2.x. The current compatibility suite proves both protocol eras in memory and over stdio, but does not exercise the
actual Streamable HTTP boundary. This leaves stateless request routing, HTTP metadata, reconnect behavior, and shared
application-state identifiers under-tested.

The published upgrade path from `1.20.0` to `1.21.0` is also only covered by independent package smoke checks. There is
no executable proof that a current client can use the old server, restart on the new server with the same bounded
artifact root, and read an artifact created before the upgrade.

## Decision

Implement one hardening package with two independent adapters:

1. A loopback-only Streamable HTTP conformance harness used by the normal test suite.
2. A network-dependent operator probe that compares two explicitly selected published package versions through
   isolated `uvx` subprocesses.

The HTTP harness belongs to test support, not production runtime. The published upgrade probe belongs under `scripts/`
and follows the project's existing pattern of pure report construction plus a thin CLI. Neither component adds an MCP
tool or changes the canonical public surface.

## Goals

- Prove modern `2026-07-28` requests work over the real Streamable HTTP application without a protocol session.
- Prove consecutive modern requests can reach different server instances that share only explicit application state.
- Prove the legacy initialize path still works over Streamable HTTP on one stable backend.
- Verify public capabilities, tools, resources, and representative tool results through the official high-level
  `mcp.Client` API.
- Prove the published `1.20.0 -> 1.21.0` upgrade preserves the old MCP surface as a subset and preserves readable
  preview artifacts across a server restart.
- Produce privacy-safe, reproducible evidence without claiming real-host UI acceptance.

## Non-Goals

- Do not implement MCP Tasks before the official Python SDK exposes SEP-2663.
- Do not deploy a public remote image-processing service.
- Do not add sticky-session infrastructure for modern requests.
- Do not claim that a loopback SDK client is Codex, Claude Desktop, Claude Code, or Cursor evidence.
- Do not require external PyPI access in the normal pull-request CI matrix.
- Do not change tools, resources, prompts, output contracts, allowed-root policy, or artifact retention.

## Architecture

### Loopback HTTP Fixture

Add a reusable async test fixture that starts an actual Uvicorn listener on `127.0.0.1` using a pre-bound ephemeral
socket. The fixture owns startup readiness, lifespan, cancellation, and teardown. Tests use the official
`Client("http://127.0.0.1:<port>/mcp", mode=...)`; they do not call ASGI handlers directly.

The fixture accepts one or more `MCPServer.streamable_http_app()` applications. A test-only dispatcher records a
bounded request trace and uses deterministic round-robin routing when multiple backends are configured. The modern
scenario configures two backends; the legacy scenario configures one stable backend because the old protocol is
allowed to retain session affinity. The dispatcher never parses a JSON-RPC body to infer the protocol era. Lifespan
events are fanned out to every configured backend before requests are accepted.

The trace records only backend index, method/path, relevant MCP header names and bounded values, and response status.
It never records request bodies, tool arguments, local paths, image bytes, authorization values, or cookies.

### Modern Stateless Scenario

Create two independent AlbumentationsX MCP server instances with the same allowed root and artifact root. The client
connects in `2026-07-28` mode and performs:

1. discovery and tool listing;
2. `run_host_smoke_check`;
3. a one-image bounded preview that returns an explicit `run_id`;
4. `get_preview_manifest` and an artifact resource read using that identifier;
5. a reconnect followed by another manifest read.

The dispatcher must show successful requests handled by both backend indices. Modern requests must carry the negotiated
protocol version and must not require `Mcp-Session-Id`. Cross-instance reads succeed because the application uses the
shared artifact root and explicit `run_id`, not hidden protocol session state.

### Legacy HTTP Scenario

Run one backend and connect with `mode="legacy"`. Assert the negotiated legacy version, complete the initialize path,
list the full-profile surface, call `search_transforms`, and read `albumentationsx://examples/client-smoke`. The test
does not require modern stateless routing semantics from the legacy protocol.

### Extension and Metadata Scenario

Inspect only public SDK discovery results and recorded HTTP headers. Create the opted-in client with the public
`advertise(EXTENSION_ID, {"mimeTypes": [APP_MIME_TYPE]})` contract and verify that the server advertises MCP Apps.
Connect a second client without that extension and verify that it still receives the standard render result. Verify
modern requests expose the routing metadata supported by the SDK, without asserting optional header values the SDK
does not guarantee.

### Published Upgrade Probe

Add `scripts/check_published_upgrade.py` with required `--from-version` and `--to-version` arguments. Each server is
started in a separate `uvx --from albumentationsx-mcp==<version> --refresh-package albumentationsx-mcp` environment over
stdio, so incompatible SDK dependency trees cannot contaminate each other.

The probe performs this matrix with the current repository's MCP 2.x client:

| Published server | Client mode | Purpose |
| --- | --- | --- |
| `from-version` | `legacy` | Confirm the old package remains usable by a current client. |
| `to-version` | `legacy` | Confirm legacy hosts remain supported after upgrade. |
| `to-version` | `2026-07-28` | Confirm the new protocol path is available. |

The old package renders one generated fixture into a temporary artifact root. The new package restarts against that
same root and reads the old manifest and contact sheet by explicit identifiers. Compatibility is additive: every old
tool, resource, resource template, and prompt identifier must remain present in the new package, while new identifiers
are allowed.

### Evidence Model

The probe emits deterministic JSON with:

- schema version, package name, from/to versions, observation date, and overall status;
- negotiated protocol per matrix row;
- counts and SHA-256 digests of sorted public identifiers;
- old-surface subset checks per contract category;
- bounded artifact continuity checks;
- failure codes and remediation, if any.

The report excludes absolute paths, environment variables, image contents, raw MCP messages, subprocess output, and
host/user identifiers. A dated committed report is machine proof only and is stored under `docs/host-evidence/` after
the online probe succeeds.

## Error Handling

- Loopback startup has a bounded timeout and reports the server phase that failed.
- Every client call and subprocess has a timeout; teardown runs even after cancellation or assertion failure.
- The upgrade probe validates both versions against PyPI's exact version endpoint before launching `uvx`.
- Missing old identifiers, unreadable old artifacts, protocol negotiation failures, or non-zero subprocess exits fail
  closed with a stable code.
- Transient package-index visibility may be retried with bounded attempts; semantic failures are never retried into a
  pass.
- Recorded evidence is written atomically only after every required check succeeds.

## Test and Automation Strategy

Normal CI adds the loopback HTTP tests on Python 3.10-3.13. Unit tests cover dispatcher routing, trace redaction,
version validation, compatibility subset logic, report determinism, timeout paths, and CLI dry-run behavior.

The external published-version probe does not run on every pull request. Add a manually dispatchable workflow with
explicit from/to version inputs and artifact upload for the JSON report. It may later become a post-release job once it
has demonstrated stable runtime and failure reporting. The first implementation run records `1.20.0 -> 1.21.0`.

Required verification:

- full pytest matrix;
- Ruff lint and format checks;
- `ty`;
- contract snapshot freshness with no public-surface removal;
- release readiness and golden MCP flows;
- one successful published `1.20.0 -> 1.21.0` probe;
- privacy scan of committed evidence.

## Success Criteria

1. Modern HTTP requests succeed across at least two backend instances without `Mcp-Session-Id` dependency.
2. A preview created through one backend is readable through another backend and after reconnect by explicit `run_id`.
3. Legacy Streamable HTTP discovery, tool invocation, and resource read pass unchanged.
4. The new server advertises MCP Apps through the public extension contract and preserves the non-App result path.
5. Every public identifier from published `1.20.0` remains available in published `1.21.0`.
6. `1.21.0` reads the manifest and contact sheet created by `1.20.0` from the same bounded artifact root.
7. The committed report contains no absolute paths or user/host identifiers.

## Release Policy

This work is test and operator hardening. It does not trigger a release by itself. If the probes expose a product defect,
fix it under the existing compatibility policy and publish `1.21.1`; otherwise merge the evidence and continue the
real-user adoption cycle before selecting `1.22.0` scope.
