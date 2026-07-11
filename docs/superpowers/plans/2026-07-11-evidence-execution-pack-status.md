# Evidence Execution Pack Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one no-write command that summarizes execution-pack structure, real-input progress, import-wizard readiness, and the next three operator actions.

**Architecture:** Create a focused orchestration module that composes the existing execution-pack audit/progress builders and the no-write import wizard. Keep `cli.py` limited to parsing and rendering, preserve validation ownership in existing modules, and expose both concise top-level fields and nested source reports.

**Tech Stack:** Python 3.10+, argparse, dataclasses, pytest subprocess fixtures, ruff, ty, uv.

---

### Task 1: Status Contract And Blocked/Unfilled States

**Files:**
- Create: `src/albumentationsx_mcp/evidence_execution_pack_status.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_execution_pack_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Generate a normal pack, invoke `evidence execution-pack-status --format json`, and assert:

```python
assert payload["status"] == "needs_real_session_input"
assert payload["writes_records"] is False
assert payload["audit_status"] == "ready_for_real_session"
assert payload["progress_status"] == "needs_real_session_input"
assert payload["import_wizard_status"] == "blocked"
assert payload["required_item_count"] == 5
assert payload["completed_item_count"] == 0
assert payload["pending_host_count"] == 2
assert payload["pending_beta_count"] == 3
assert payload["import_ready_command_available"] is False
assert len(payload["next_commands"]) <= 3
```

Delete `operator-checklist.md`, rerun the command, and assert `status == "blocked"`, the missing-file blocker is
reported, `import_wizard_status == "not_run"`, and the canonical record files remain unchanged.

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_evidence_execution_pack_cli.py -k 'pack_status' -q
```

Expected: fail because `execution-pack-status` is not registered.

- [ ] **Step 3: Implement the status module and CLI adapter**

Add an immutable request with `input_dir`, `host_records_path`, and `beta_records_path`. Build audit and progress first.
If the audit is valid, run `build_evidence_import_wizard` with discovered host manifest paths, the pack's
`beta-responses` directory, and `import_ready=False`. Return the specified top-level contract plus `audit`, `progress`,
`import_wizard`, and a non-fabrication policy. Add deterministic JSON and Markdown renderers.

Register this parser:

```python
execution_pack_status = subparsers.add_parser(
    "execution-pack-status",
    help="Summarize execution-pack audit, progress, and import readiness without writing records.",
)
execution_pack_status.add_argument("--input-dir", type=Path, required=True)
execution_pack_status.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
execution_pack_status.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
execution_pack_status.add_argument("--format", choices=["json", "markdown"], default="json")
execution_pack_status.add_argument("--output", type=Path, default=None)
```

- [ ] **Step 4: Verify GREEN**

Run the RED command again. Expected: both status tests pass.

### Task 2: Ready State And Renderer Coverage

**Files:**
- Modify: `tests/test_evidence_execution_pack_cli.py`
- Modify: `src/albumentationsx_mcp/evidence_execution_pack_status.py`

- [ ] **Step 1: Write a failing ready-state test**

Generate a pack, replace both host manifests and all three beta responses with valid reviewer-observed fixture data,
and invoke the status command with temporary empty host and beta record files. Assert:

```python
assert payload["status"] == "ready_for_import_review"
assert payload["writes_records"] is False
assert payload["completed_item_count"] == payload["required_item_count"] == 5
assert payload["pending_host_count"] == 0
assert payload["pending_beta_count"] == 0
assert payload["import_wizard_status"] == "ready_to_import"
assert payload["import_ready_command_available"] is True
assert "--import-ready" in payload["next_commands"][0]
```

Also request Markdown output and assert its heading, status, completed count, import readiness, blockers, and next-command
sections.

- [ ] **Step 2: Verify RED**

Run the new ready/Markdown tests and confirm they fail on missing or incomplete behavior.

- [ ] **Step 3: Complete state selection and rendering**

Use `ready_for_import_review` only when progress and wizard both agree. Prefix unexpected wizard blockers with
`import_wizard:` and expose no import-ready command unless the wizard returns `ready_to_import`. Limit `next_commands`
to the first three unique actions.

- [ ] **Step 4: Verify GREEN and refactor**

Run:

```bash
uv run pytest tests/test_evidence_execution_pack_cli.py -q
uv run ruff check src/albumentationsx_mcp/evidence_execution_pack_status.py src/albumentationsx_mcp/cli.py tests/test_evidence_execution_pack_cli.py
uv run ty check
```

Expected: all commands pass.

### Task 3: Public Docs, Packaged Skill, And Release Gate

**Files:**
- Modify: `docs/USAGE.md`
- Modify: `docs/REAL_EVIDENCE_INPUT_CHECKLIST.md`
- Modify: `skills/albumentationsx-mcp/SKILL.md`
- Modify: `tests/test_cli_evidence_beta.py`
- Modify: `tests/test_skills_package.py`

- [ ] **Step 1: Make documentation contract tests fail**

Require these strings in the existing tests:

```text
albu-mcp evidence execution-pack-status --input-dir evidence-session --format markdown
albu-mcp evidence execution-pack-status --input-dir evidence-session
```

Run the two documentation tests and confirm the missing references fail.

- [ ] **Step 2: Document one-command operator status**

Add the command next to audit/progress in `docs/USAGE.md`, include it in the report-only helper list, and explain in the
real evidence checklist that it returns structure, completion, wizard readiness, and bounded next actions without
writing records. Add the command to the packaged skill while keeping `SKILL.md` at or below 450 words.

- [ ] **Step 3: Verify focused contracts**

Run:

```bash
uv run pytest tests/test_evidence_execution_pack_cli.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli tests/test_skills_package.py::test_skills_sh_package_has_installable_agent_skill -q
uv run ruff check .
uv run ruff format --check .
uv run ty check
```

Expected: all commands pass.

- [ ] **Step 4: Run the complete release gate**

Run:

```bash
uv run pytest -q
uv run albu-mcp evidence template-guard --host-manifest docs/operator-packets/codex-evidence-session-manifest.json --host-manifest docs/operator-packets/claude-code-evidence-session-manifest.json --beta-dir docs/beta-response-templates --strict --format json
uv run albu-mcp evidence preflight --format json
uv build
git diff --check
```

Expected: 0 test failures, template guard `passed`, preflight remains report-only, build exits 0, and the diff has no
whitespace errors.
