# Compatibility Policy

AlbumentationsX MCP treats the MCP-facing tool, resource, prompt, and package metadata surface as the public contract.
Changes to that surface must be deliberate and covered by tests.

## Public Contract

The public contract includes:

- MCP tool names, descriptions, and input schemas;
- MCP resource URIs and resource template parameters;
- MCP prompt names and arguments;
- response fields documented in README, usage docs, recipes, or golden evals;
- `server.json` package identity, version, registry package name, and transport metadata.

Three reviewed snapshot layers guard this contract:

- `scripts/export_cli_contract.py` writes the server and operator CLI parser snapshot used by
  `tests/test_cli_contract_snapshot.py`.
- `scripts/export_mcp_contract.py` writes the tool/resource/prompt surface snapshot used by
  `tests/test_mcp_contract_snapshot.py`.
- `scripts/export_output_contracts.py` writes representative output payload snapshots used by
  `tests/test_output_contract_snapshots.py`.

## Compatible Changes

Compatible changes may ship in minor releases:

- adding an optional tool parameter with a default;
- adding a new tool, resource, prompt, workflow, recipe, or response field;
- improving descriptions without changing accepted inputs;
- adding new enum values only when older hosts can ignore or pass them through safely;
- tightening internal validation when invalid input was already outside the documented contract.

Capability profiles are additive configuration views. `full` defines the complete v1.x public contract and remains the
default. A focused profile intentionally omits items outside its declared view; that is not a removal from `full`.
Every profile must be generated from the same canonical registration manifest and pass dependency-closure tests. A
change to the default profile, or removal from `full`, requires the major-release migration process below.

Compatible changes still need changelog notes when they affect host-visible workflows, reports, recommendations, preview
artifacts, safety boundaries, or release metadata.

## Breaking Changes

Breaking changes wait for a major release unless the current behavior is unsafe or unusable:

- removing or renaming a public tool, resource, prompt, response field, or `server.json` package identity;
- making an optional tool input required;
- changing a field type or enum meaning in a way existing hosts cannot handle;
- changing artifact URI semantics, allowed-root behavior, or retention behavior in a way that can lose user data;
- changing report content contracts that tests or host workflows rely on.

When a breaking change is necessary, document the migration path in the changelog and usage docs before release.

## Deprecations

Prefer additive migration:

1. Add the replacement contract first.
2. Keep the old contract working for at least one minor release.
3. Document the replacement in README, usage docs, and changelog.
4. Remove the deprecated contract only in a major release.

## Required Coverage

Every public contract change needs at least one of these checks:

- contract snapshot update for tool/resource/prompt surface changes;
- output contract snapshot update for representative response shape changes;
- golden MCP eval coverage for end-to-end host workflow changes;
- focused pytest coverage for storage, report, preview, ranking, recipe, or pipeline behavior;
- release version guard updates for package or registry metadata changes.

If a snapshot diff is intentional, commit it with the code or docs that explain the change.
Use `scripts/classify_contract_drift.py` or the classification printed by `scripts/check_contract_snapshots.py` to
separate compatible additions, documentation-only edits, output shape drift, and breaking removals.

Regenerate snapshots with:

```bash
uv run python scripts/export_cli_contract.py --output tests/fixtures/snapshots/cli_contract.json
uv run python scripts/export_mcp_contract.py --output tests/fixtures/snapshots/mcp_contract.json
uv run python scripts/export_output_contracts.py --output tests/fixtures/snapshots/output_contracts.json
```

Check that committed snapshots are fresh with:

```bash
uv run python scripts/check_contract_snapshots.py
```

This contract snapshot freshness guard fails when committed tool, resource, prompt, or output snapshots are stale.
