# Pack-Native Status Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make generated evidence execution packs contain one copy-ready, no-write status handoff before any reviewed record import.

**Architecture:** Keep generated-artifact ownership in `evidence_execution_pack.py`. Add one private command builder reused by the pack README and post-session runbook, then verify the rendered shell command end to end under paths containing spaces. Update public docs and the packaged skill without changing CLI behavior or evidence validators.

**Tech Stack:** Python 3.10+, argparse CLI, `shlex`, pytest fixtures/subprocess integration tests, ruff, ty, uv.

---

### Task 1: Generated Pack Status Handoff

**Files:**
- Modify: `src/albumentationsx_mcp/evidence_execution_pack.py`
- Modify: `tests/test_evidence_execution_pack_cli.py`

- [ ] **Step 1: Write the failing generated-artifact integration test**

Import `shlex` and add a test that creates host/beta record files under `record files/`, generates a pack under
`evidence session/`, and builds this expected command with `shlex.join`:

```python
expected_command = shlex.join(
    [
        "albu-mcp",
        "evidence",
        "execution-pack-status",
        "--input-dir",
        str(output_dir),
        "--host-records",
        str(host_records),
        "--beta-records",
        str(beta_records),
        "--format",
        "markdown",
        "--output",
        str(output_dir / "status.md"),
    ]
)
```

Assert the identical command appears in `README.md` and `post-session-commands.md`, `status.md` is initially absent,
and the post-session headings are ordered as `Pack Status`, validation, `Import Wizard (No Write)`, then
`Reviewed Import (Writes Records)`.

Parse `expected_command` with `shlex.split`, replace the console entry point with
`python -m albumentationsx_mcp`, and execute it. Assert `status.md` contains:

```text
Status: `needs_real_session_input`
Writes records: `false`
```

Assert the host and beta record files are byte-for-byte unchanged.

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_evidence_execution_pack_cli.py -k 'embeds_runnable_status_handoff' -q
```

Expected: fail because generated artifacts do not contain the status command.

- [ ] **Step 3: Implement one canonical status command builder**

Add:

```python
def _execution_pack_status_command(request: EvidenceExecutionPackRequest) -> str:
    return (
        "albu-mcp evidence execution-pack-status "
        f"--input-dir {_quote_path(request.output_dir)} "
        f"--host-records {_quote_path(request.host_records_path)} "
        f"--beta-records {_quote_path(request.beta_records_path)} "
        f"--format markdown --output {_quote_path(request.output_dir / 'status.md')}"
    )
```

Use it in both renderers. The README explains that the report is no-write and should be refreshed after edits.
The post-session runbook places status first, retains per-input validation and preflight, renames the no-write wizard
section, and moves `--import-ready` into a separate reviewed-import section with explicit readiness and approval rules.

- [ ] **Step 4: Verify GREEN and focused quality**

Run:

```bash
uv run pytest tests/test_evidence_execution_pack_cli.py -q
uv run ruff check src/albumentationsx_mcp/evidence_execution_pack.py tests/test_evidence_execution_pack_cli.py
uv run ruff format --check src/albumentationsx_mcp/evidence_execution_pack.py tests/test_evidence_execution_pack_cli.py
uv run ty check
```

Expected: all commands pass.

### Task 2: Public Docs And Packaged Skill

**Files:**
- Modify: `docs/USAGE.md`
- Modify: `docs/REAL_EVIDENCE_INPUT_CHECKLIST.md`
- Modify: `CHANGELOG.md`
- Modify: `skills/albumentationsx-mcp/SKILL.md`
- Modify: `tests/test_cli_evidence_beta.py`
- Modify: `tests/test_skills_package.py`

- [ ] **Step 1: Make documentation contracts fail**

Change the existing expected status command in both tests to require:

```text
albu-mcp evidence execution-pack-status --input-dir evidence-session --format markdown --output evidence-session/status.md
```

Run:

```bash
uv run pytest tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli tests/test_skills_package.py::test_skills_sh_package_has_installable_agent_skill -q
```

Expected: both tests fail because `--output evidence-session/status.md` is not documented.

- [ ] **Step 2: Update docs and skill minimally**

Update the usage command, checklist command, and packaged skill bullet to include the report path. Explain that generated
packs already contain this handoff and that `status.md` must be refreshed after evidence edits. Keep the skill body at
or below 450 words by shortening adjacent install prose rather than dropping safety rules. Add one Unreleased changelog
entry for the generated status handoff.

- [ ] **Step 3: Verify GREEN and skill size**

Run:

```bash
uv run pytest tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli tests/test_skills_package.py::test_skills_sh_package_has_installable_agent_skill -q
awk 'BEGIN { separators=0; words=0 } /^---$/ { separators++; next } separators >= 2 { words += NF } END { print words }' skills/albumentationsx-mcp/SKILL.md
```

Expected: tests pass and the skill body is at most 450 words.

### Task 3: Full Verification And Integration

**Files:**
- Verify all changed files and generated contracts.

- [ ] **Step 1: Run the complete local gate**

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest -q
uv run albu-mcp evidence template-guard --host-manifest docs/operator-packets/codex-evidence-session-manifest.json --host-manifest docs/operator-packets/claude-code-evidence-session-manifest.json --beta-dir docs/beta-response-templates --strict --format json
uv run albu-mcp evidence preflight --format json
uv run python scripts/check_release_readiness.py
uv build
git diff --check
```

Expected: quality checks pass, template guard reports `passed`, preflight remains no-write and honestly blocked on
missing external evidence, release readiness passes its configured policy, and wheel/sdist build succeeds.

- [ ] **Step 2: Review and integrate**

Review `origin/main..HEAD`, push `codex/pack-native-status-handoff`, open a ready PR, wait for Python 3.10-3.13 CI,
squash-merge, delete the remote feature branch, fast-forward local `main`, and rerun the focused execution-pack suite.
