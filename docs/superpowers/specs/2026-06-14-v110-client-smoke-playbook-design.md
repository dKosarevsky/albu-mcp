# V1.1 Client Smoke Playbook Design

## Goal

Add a small, read-only MCP host example that tells clients how to verify a fresh AlbumentationsX MCP connection before
starting preview work.

## Scope

This is a compatible minor extension. It adds one resource, one host example entry, documentation, tests, and an updated
MCP contract snapshot. It does not add mutating tools, new filesystem access, new dependencies, or response changes for
existing tools.

## Design

The existing `workflows.py` module already owns agent-legible workflow and host example contracts. The new
`client-smoke` example belongs there so the FastMCP adapter stays thin and resource output remains deterministic.

The example should be intentionally short:

- inspect `albumentationsx://capabilities`;
- inspect `albumentationsx://recipes/catalog`;
- call `recommend_recipe` for a low-intensity classification workflow;
- call `validate_pipeline` on the recommended pipeline before rendering user data.

The server exposes it as `albumentationsx://examples/client-smoke`. The capabilities resource lists the URI next to the
existing example resources. `docs/INSTALL.md`, `docs/USAGE.md`, and `docs/RECIPES.md` link the smoke playbook so new MCP
host users can find it after installation.

## Testing

Use TDD:

- `tests/test_workflows.py` first expects `client-smoke` in `list_host_examples()`;
- `tests/test_server.py` first expects the new resource and capabilities URI;
- `tests/test_project_scaffolding.py` guards documentation references;
- `scripts/export_mcp_contract.py` refreshes `tests/fixtures/snapshots/mcp_contract.json` after implementation.

Full release verification remains `pytest`, `ruff`, `ruff format --check`, `ty`, golden evals, version check, and build.
