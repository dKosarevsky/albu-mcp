# v0.13 Install Guide Readiness Design

## Context

`v0.12.0` stabilized the MCP-facing surface with public contract and output snapshots. The remaining v1-readiness gap is
not runtime behavior; it is host-facing onboarding. Users should be able to install the published server from PyPI,
connect it from common MCP hosts, constrain local filesystem access, smoke-test the server, and understand what to check
before filing an issue.

The official MCP documentation currently emphasizes local stdio servers, explicit user approval for local access, PyPI
package metadata in `server.json`, README `mcp-name` ownership verification for PyPI packages, and safe handling of
local server commands. Claude Code documents direct JSON import for stdio server configs. This project already follows
those conventions through `server.json`, PyPI publishing, MCP Registry publishing, and bounded local roots.

## Scope

Add an install-focused documentation pass without changing the public MCP API:

- create one canonical install guide with PyPI, local checkout, Claude Desktop-style JSON, Claude Code JSON import,
  Cursor-style JSON, Codex-style TOML, allowed-root/artifact-root examples, smoke checks, troubleshooting, and safety
  notes;
- keep README concise and route detailed host setup to the canonical guide;
- make examples copyable and consistent with the guide;
- add focused tests that verify the guide and example files stay present and aligned with the published package command.

Out of scope:

- no new MCP tools, resources, prompts, or output fields;
- no new client-specific automation;
- no remote HTTP deployment guide;
- no `v1.0.0` tag yet.

## Design

`docs/INSTALL.md` becomes the durable onboarding artifact. It should prefer the published PyPI package via `uvx`, because
that matches MCP Registry distribution and avoids requiring a git checkout. Local checkout instructions remain available
for contributors.

The guide uses three installation patterns:

1. **Published package**: `uvx --from albumentationsx-mcp albumentationsx-mcp`.
2. **Bounded local data access**: add `--allowed-root` and `--artifact-root` so previews can only read intended images and
   write artifacts to an explicit directory.
3. **Local development**: `uv run albumentationsx-mcp` from the repository checkout.

Host examples should avoid hard-coding client UI paths where those products change often. The guide can show the stable
config shapes already used by the repository:

- JSON `mcpServers` for Claude Desktop-style and Cursor-style hosts;
- `claude mcp add-json` for Claude Code users who prefer CLI import;
- TOML `mcp_servers` for Codex-style configuration.

The safety section should be direct: install from PyPI or this repository, use absolute paths, scope allowed roots to the
smallest image directory needed, keep artifacts separate from source datasets, and run the manual help command before
starting a host session.

## Testing

Add a project-scaffolding test that reads `docs/INSTALL.md` and the host example files. It should assert:

- the install guide exists and is linked from README and usage docs;
- the guide includes PyPI, MCP Registry, Claude Desktop, Claude Code, Cursor, Codex, allowed root, artifact root, smoke
  checks, and troubleshooting sections;
- JSON/TOML examples use the same package command shape: `uvx --from albumentationsx-mcp albumentationsx-mcp`;
- the README v1-readiness note names the install guide as the remaining host-facing readiness artifact.

No snapshot regeneration is required because the public MCP contract does not change.
