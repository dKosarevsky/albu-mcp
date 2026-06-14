# Client Smoke Golden Eval Design

## Goal

Make the `albumentationsx://examples/client-smoke` playbook executable in the golden MCP eval suite so release checks
prove that a real stdio MCP client can read the smoke resource and follow its safe setup path.

## Scope

This is a test/eval hardening change. It does not add MCP tools, resources, prompts, response fields, package
dependencies, or release-version metadata. It adds one golden scenario and small runner support for resource reads.

## Design

The current runner already starts the server over stdio, calls typed tools, and fails on the first contract mismatch. The
new scenario should stay lightweight and run before preview-heavy scenarios:

1. read `albumentationsx://examples/client-smoke`;
2. assert the playbook contains the expected trigger phrase and step tools/resources;
3. read `albumentationsx://capabilities` and `albumentationsx://recipes/catalog`;
4. call `recommend_recipe` for low-intensity classification;
5. call `validate_pipeline` on the returned pipeline.

The implementation belongs in `scripts/run_golden_evals.py`. It should add a small resource helper and a
`_run_client_smoke` flow while leaving existing preview scenarios unchanged.

## Testing

Use TDD:

- update `tests/test_golden_evals.py` to expect the new scenario and runner support;
- add the scenario to `evals/golden_mcp_scenarios.yaml`;
- confirm the focused test fails before runner support exists;
- implement the helper and flow;
- run `uv run pytest tests/test_golden_evals.py -q` and `uv run python scripts/run_golden_evals.py`.
