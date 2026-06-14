# Client Smoke Golden Eval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an executable golden eval scenario for the `albumentationsx://examples/client-smoke` MCP resource.

**Architecture:** Keep runtime server code unchanged. Extend `scripts/run_golden_evals.py` with a focused resource-read
helper and a client-smoke flow, then add one YAML scenario and tests that prove the scenario is part of the default suite.

**Tech Stack:** Python 3.10+, MCP stdio client, pytest, PyYAML, uv, ruff, ty.

---

### Task 1: RED Test And Scenario

**Files:**
- Modify: `tests/test_golden_evals.py`
- Modify: `evals/golden_mcp_scenarios.yaml`

- [ ] Add `client_smoke_resource_flow` to the expected scenario set in `test_golden_eval_assets_are_present`.
- [ ] Assert the scenario has `client_smoke: true` and required resource URIs.
- [ ] Add the YAML scenario with `task: classification`, `intensity: low`, `targets: ["image"]`, `client_smoke: true`, and expected resources.
- [ ] Run `uv run pytest tests/test_golden_evals.py::test_golden_eval_assets_are_present -q`.
- [ ] Expected result: failure because runner support for `client_smoke` is not present yet.

### Task 2: Runner Resource Flow

**Files:**
- Modify: `scripts/run_golden_evals.py`

- [ ] Add `_read_resource_json(session, uri)` that calls `session.read_resource(uri)` and parses text JSON.
- [ ] Add `_run_client_smoke(session, scenario)` that reads the smoke playbook, capabilities, and recipes, then calls `recommend_recipe` and `validate_pipeline`.
- [ ] Call `_run_client_smoke` at the start of `_run_scenario` when `scenario["client_smoke"]` is true.
- [ ] Run `uv run pytest tests/test_golden_evals.py -q`.
- [ ] Run `uv run python scripts/run_golden_evals.py`.

### Task 3: Verification And Commit

**Files:**
- Modified eval, runner, tests, and plan/spec docs.

- [ ] Run `uv run pytest`.
- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run ruff format --check .`.
- [ ] Run `uv run ty check`.
- [ ] Commit as `test: add client smoke golden eval`.
- [ ] Push `main`. No tag is required because this does not change package runtime behavior.
