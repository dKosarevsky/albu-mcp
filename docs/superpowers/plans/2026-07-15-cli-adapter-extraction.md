# CLI Adapter Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce `cli.py` to a compatibility facade over focused command adapters while preserving all 9 command
groups, 84 subcommands, parser schemas, output behavior, exit codes, and console entrypoints.

**Architecture:** Capture the existing argparse tree as a canonical contract before moving code. Introduce pure CLI
surface declarations, focused parser/handler modules, and one ordered dispatch registry; keep argparse and namespace
objects inside `adapters.cli`, and retain compatibility aliases in `albumentationsx_mcp.cli`.

**Tech Stack:** Python 3.10+, argparse, Pydantic, dataclasses, pytest fixtures/parametrization, Ruff, ty.

---

### Task 1: Canonical CLI Contract Snapshot

**Files:**
- Create: `scripts/export_cli_contract.py`
- Create: `tests/fixtures/snapshots/cli_contract.json`
- Create: `tests/test_cli_contract_snapshot.py`
- Modify: `scripts/check_contract_snapshots.py`

- [ ] **Step 1: Write failing snapshot tests**

Add tests that require a deterministic exporter and committed fixture:

```python
def test_cli_contract_snapshot_matches_public_surface() -> None:
    expected = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert build_cli_contract_snapshot() == expected


def test_cli_contract_has_complete_inventory() -> None:
    snapshot = build_cli_contract_snapshot()
    assert snapshot["dispatch"]["groups"] == [
        "activation", "beta", "distribution", "evidence", "host", "intake", "preview", "rc", "trust"
    ]
    assert sum(len(group["commands"]) for group in snapshot["groups"].values()) == 84
```

Also assert that `dump_cli_contract_snapshot` reproduces the fixture byte-for-byte with sorted JSON keys and one final
newline.

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest -q tests/test_cli_contract_snapshot.py`

Expected: import failure because `scripts.export_cli_contract` does not exist.

- [ ] **Step 3: Implement parser capture and canonical serialization**

Use `unittest.mock.patch.object(argparse.ArgumentParser, "parse_args", ...)` to capture the parser created by each
existing `_run_*` compatibility function before any handler executes. Serialize recursively:

```python
{
    "description": parser.description,
    "options": [
        {
            "flags": action.option_strings,
            "dest": action.dest,
            "action": type(action).__name__,
            "required": action.required,
            "nargs": action.nargs,
            "choices": list(action.choices) if action.choices is not None else None,
            "default": _json_safe(action.default),
            "type": _type_name(action.type),
            "help": action.help,
        }
    ],
    "commands": {name: _parser_entry(child) for name, child in subparser_action.choices.items()},
}
```

Omit generated `prog` values and argparse's implicit help action so the fixture captures the authored contract rather
than process-specific text. Capture the default server parser separately and use sorted group names from `_SUBCOMMANDS`.

- [ ] **Step 4: Generate and verify the baseline**

Run:

```bash
uv run python scripts/export_cli_contract.py --output tests/fixtures/snapshots/cli_contract.json
uv run pytest -q tests/test_cli_contract_snapshot.py
uv run python scripts/check_contract_snapshots.py
uv run ruff check scripts/export_cli_contract.py tests/test_cli_contract_snapshot.py
uv run ty check scripts/export_cli_contract.py tests/test_cli_contract_snapshot.py
```

Expected: 9 groups, 84 commands, and a canonical fresh fixture.

- [ ] **Step 5: Commit the baseline**

```bash
git add scripts/export_cli_contract.py scripts/check_contract_snapshots.py \
  tests/fixtures/snapshots/cli_contract.json tests/test_cli_contract_snapshot.py
git commit -m "test: snapshot the CLI contract"
```

### Task 2: CLI Surface Contract And Small Adapters

**Files:**
- Create: `src/albumentationsx_mcp/adapters/cli/__init__.py`
- Create: `src/albumentationsx_mcp/adapters/cli/contracts.py`
- Create: `src/albumentationsx_mcp/adapters/cli/runtime.py`
- Create: `src/albumentationsx_mcp/adapters/cli/preview.py`
- Create: `src/albumentationsx_mcp/adapters/cli/intake.py`
- Create: `tests/test_cli_adapters.py`

- [ ] **Step 1: Write failing pure surface and parser-fragment tests**

Define the expected contract usage in tests:

```python
surfaces = combine_cli_group_surfaces(
    (
        CliGroupSurface(group="host", commands=("setup-probe", "next-action")),
        CliGroupSurface(group="preview", commands=("first-pack",)),
    )
)
assert surfaces.command_paths == ("host setup-probe", "host next-action", "preview first-pack")
```

Parameterize duplicate checks for empty group names, duplicate groups, empty commands, and duplicate commands within a
group. Add parser-fragment comparisons for `host`, `preview`, and `intake`, plus server options, against
`cli_contract.json`.

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest -q tests/test_cli_adapters.py`

Expected: import failure for `albumentationsx_mcp.adapters.cli.contracts`.

- [ ] **Step 3: Implement pure declarations**

Add frozen, slotted `CliGroupSurface` and `CombinedCliSurface` dataclasses. `combine_cli_group_surfaces` must preserve
group and command declaration order and return fully qualified command paths. This module must not import argparse,
Pydantic, domain modules, environment accessors, or the legacy CLI facade.

- [ ] **Step 4: Extract runtime, preview, and intake adapters**

Move code without changing parser descriptions, flags, defaults, choices, output strings, or exception translation:

- `runtime.py`: server parser/runner and host `setup-probe`/`next-action` parser and handlers;
- `preview.py`: preview `first-pack` parser and handler;
- `intake.py`: intake `bundle` parser and handler.

Each grouped module exports `SURFACE`, `build_<group>_parser()`, and `run_<group>(argv)`. `runtime.py` additionally
exports `build_server_parser()` and `run_server(argv)`. Runner structure remains:

```python
def run_preview(argv: list[str]) -> None:
    args = build_preview_parser().parse_args(argv)
    try:
        sys.stdout.write(handle_preview_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc
```

- [ ] **Step 5: Verify exact fragments and representative behavior**

Run:

```bash
uv run pytest -q tests/test_cli_adapters.py tests/test_host_setup_probe.py tests/test_host_trust_next_action.py \
  tests/test_intake_automation_cli.py
uv run ruff check src/albumentationsx_mcp/adapters/cli tests/test_cli_adapters.py
uv run ruff format --check src/albumentationsx_mcp/adapters/cli tests/test_cli_adapters.py
uv run ty check src/albumentationsx_mcp/adapters/cli tests/test_cli_adapters.py
```

- [ ] **Step 6: Commit small adapters**

```bash
git add src/albumentationsx_mcp/adapters/cli tests/test_cli_adapters.py
git commit -m "refactor: extract runtime CLI adapters"
```

### Task 3: Activation And Product-Fix Adapters

**Files:**
- Create: `src/albumentationsx_mcp/adapters/cli/activation.py`
- Create: `src/albumentationsx_mcp/adapters/cli/product_fix.py`
- Modify: `tests/test_cli_adapters.py`

- [ ] **Step 1: Add failing activation ownership tests**

Declare `activation` as one public group with 24 commands. Keep 11 cycle/proof commands in `activation.py` and 13
product-fix commands in `product_fix.py`. Assert that the composed parser command order and every recursive parser
entry equal the `activation` fragment in the baseline snapshot.

The activation-owned command set is:

```text
command-center, runbook, proof-sprint, execution-workspace, real-proof-run, evidence-first-cycle,
acquisition-cycle, evidence-cockpit, evidence-product-loop, real-adoption-cycle, first-product-fix,
product-fix-closure-import, product-fix-closure-pack, product-fix-closure-pipeline,
product-fix-closure-receipt, product-fix-closure-snapshot, product-fix-closure-runbook,
product-fix-implementation-plan, product-fix-execution-guard, product-fix-validation,
product-fix-outcome, product-fix-outcome-capture, product-fix-outcome-import-guard,
product-fix-outcome-rehearsal
```

- [ ] **Step 2: Confirm RED and extract parser registration**

Run: `uv run pytest -q tests/test_cli_adapters.py -k activation`

Move `_add_activation_*_parser` functions into the two modules. `activation.build_activation_parser()` creates the
root parser, invokes its local registrars, then `product_fix.register_product_fix_parsers(subparsers)` in the same order
as the baseline.

- [ ] **Step 3: Extract handlers with explicit dispatch maps**

Move `_handle_activation_*` functions unchanged. Export `PRODUCT_FIX_HANDLERS` from `product_fix.py`; merge it after the
11 cycle handlers in `activation.py`. Unknown commands keep the exact `unsupported activation command` error.

- [ ] **Step 4: Verify parser identity and command behavior**

Run:

```bash
uv run pytest -q tests/test_cli_adapters.py -k activation
uv run pytest -q tests/test_activation_cli.py tests/test_real_evidence_beta_acquisition_cli.py \
  tests/test_real_evidence_cockpit_cli.py tests/test_real_adoption_cycle_cli.py \
  tests/test_product_fix_closure_pipeline_cli.py tests/test_product_fix_outcome_rehearsal_cli.py
uv run ruff check src/albumentationsx_mcp/adapters/cli tests/test_cli_adapters.py
uv run ty check src/albumentationsx_mcp/adapters/cli tests/test_cli_adapters.py
```

- [ ] **Step 5: Commit activation extraction**

```bash
git add src/albumentationsx_mcp/adapters/cli/activation.py \
  src/albumentationsx_mcp/adapters/cli/product_fix.py tests/test_cli_adapters.py
git commit -m "refactor: extract activation CLI adapters"
```

### Task 4: Evidence And Beta Adapters

**Files:**
- Create: `src/albumentationsx_mcp/adapters/cli/evidence.py`
- Create: `src/albumentationsx_mcp/adapters/cli/evidence_capture.py`
- Create: `src/albumentationsx_mcp/adapters/cli/evidence_guidance.py`
- Create: `src/albumentationsx_mcp/adapters/cli/beta.py`
- Modify: `tests/test_cli_adapters.py`

- [ ] **Step 1: Add failing evidence/beta surface tests**

Assert exact baseline fragments for 33 `evidence` commands and 12 `beta` commands. `evidence.py` owns composition and
dispatch only; capture/import/execution-pack/template/preflight commands belong to `evidence_capture.py`, while
packet/proof/doctor/status commands belong to `evidence_guidance.py`.

- [ ] **Step 2: Confirm RED and extract evidence registration**

Run: `uv run pytest -q tests/test_cli_adapters.py -k 'evidence or beta'`

Move recording/import/session/execution-pack/template/preflight parser builders and handlers to `evidence_capture.py`.
Move run-session, packet, collect, proof, transition, transcript, doctor, unblock, status, and close-host builders and
handlers to `evidence_guidance.py`. Export registrar functions and handler dictionaries from each module.

- [ ] **Step 3: Compose evidence without cross-module namespace mutation**

`evidence.build_evidence_parser()` creates one subparser action and calls the two registrars in existing order.
`handle_evidence_command` performs a deterministic dictionary lookup across the two exported handler maps and retains
the exact unsupported-command error. No domain module imports an argparse type.

- [ ] **Step 4: Extract beta commands unchanged**

Move beta parser construction and handlers into `beta.py`, including response validation/import/template commands.
Export `SURFACE`, `build_beta_parser`, and `run_beta`.

- [ ] **Step 5: Verify parser and output contracts**

Run:

```bash
uv run pytest -q tests/test_cli_adapters.py -k 'evidence or beta'
uv run pytest -q tests/test_cli_evidence_beta.py tests/test_real_evidence_intake_cli.py \
  tests/test_evidence_execution_pack_cli.py tests/test_evidence_proof_loop_cli.py \
  tests/test_evidence_import_wizard_cli.py tests/test_beta_report_cli.py
uv run ruff check src/albumentationsx_mcp/adapters/cli tests/test_cli_adapters.py
uv run ruff format --check src/albumentationsx_mcp/adapters/cli tests/test_cli_adapters.py
uv run ty check src/albumentationsx_mcp/adapters/cli tests/test_cli_adapters.py
```

- [ ] **Step 6: Commit evidence extraction**

```bash
git add src/albumentationsx_mcp/adapters/cli tests/test_cli_adapters.py
git commit -m "refactor: extract evidence CLI adapters"
```

### Task 5: Release Composition And Compatibility Facade

**Files:**
- Create: `src/albumentationsx_mcp/adapters/cli/release.py`
- Create: `src/albumentationsx_mcp/adapters/cli/registration.py`
- Create: `src/albumentationsx_mcp/adapters/cli/app.py`
- Modify: `src/albumentationsx_mcp/adapters/cli/__init__.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `tests/test_cli_adapters.py`
- Modify: `tests/test_cli_contract_snapshot.py`

- [ ] **Step 1: Add failing release/composition/facade tests**

Tests must assert:

```python
assert len(COMBINED_CLI_SURFACE.groups) == 9
assert len(COMBINED_CLI_SURFACE.command_paths) == 84
assert tuple(GROUP_RUNNERS) == (
    "activation", "beta", "distribution", "evidence", "host", "intake", "preview", "rc", "trust"
)
source = Path("src/albumentationsx_mcp/cli.py").read_text(encoding="utf-8")
assert "add_parser(" not in source
assert "build_" not in source
assert len(source.splitlines()) <= 120
```

Also assert that both console scripts still target `albumentationsx_mcp.cli:main` and that compatibility aliases
`_run_server`, `_run_activation_cli`, `_run_beta_cli`, `_run_distribution_cli`, `_run_evidence_cli`, `_run_host_cli`,
`_run_intake_cli`, `_run_preview_cli`, `_run_rc_cli`, and `_run_trust_cli` remain callable.

- [ ] **Step 2: Extract release-facing groups**

Move RC, distribution, and trust parser/handler code to `release.py` with three surfaces and three parser factories.
Keep report-only semantics, output text, file writes, and `(ValidationError, ValueError) -> SystemExit(1)` behavior.

- [ ] **Step 3: Implement ordered registry**

`registration.py` validates all nine surfaces, exposes `CLI_GROUP_SURFACES`, `COMBINED_CLI_SURFACE`, and the stable
`GROUP_RUNNERS` mapping. It verifies at import/test time that each parser's direct subcommand names exactly equal its
declared `SURFACE.commands`; no registry function may read environment variables or execute a handler.

- [ ] **Step 4: Implement app dispatch and thin facade**

`app.main(argv)` preserves current fallback semantics: a recognized first token dispatches a CLI group; otherwise the
same argv is parsed as server options. Replace `cli.py` with imports and compatibility aliases only:

```python
from albumentationsx_mcp.adapters.cli.app import main, run_cli_subcommand as _run_cli_subcommand
from albumentationsx_mcp.adapters.cli.registration import GROUP_RUNNERS
from albumentationsx_mcp.adapters.cli.runtime import run_server as _run_server

_SUBCOMMANDS = frozenset(GROUP_RUNNERS)
```

Re-export each legacy private runner alias for the contract exporter and any downstream diagnostic imports.

- [ ] **Step 5: Prove full CLI contract identity**

Run:

```bash
uv run pytest -q tests/test_cli_adapters.py tests/test_cli_contract_snapshot.py
uv run python scripts/check_contract_snapshots.py
git diff --exit-code -- tests/fixtures/snapshots/cli_contract.json
uv run pytest -q tests/test_activation_cli.py tests/test_cli_evidence_beta.py \
  tests/test_distribution_trust_cli.py tests/test_rc_reopen_cli.py tests/test_intake_automation_cli.py
```

Expected: the baseline fixture is unchanged and representative commands preserve stdout, stderr, writes, and exit
codes.

- [ ] **Step 6: Commit the facade switch**

```bash
git add src/albumentationsx_mcp/adapters/cli src/albumentationsx_mcp/cli.py \
  tests/test_cli_adapters.py tests/test_cli_contract_snapshot.py
git commit -m "refactor: compose CLI adapters"
```

### Task 6: Boundary Guards And Full Verification

**Files:**
- Create: `tests/test_architecture_boundaries.py`
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/plans/2026-07-15-cli-adapter-extraction.md`

- [ ] **Step 1: Add transport-boundary tests**

Parse imports with `ast` and assert that modules outside `albumentationsx_mcp.adapters`, `server.py`, and the `cli.py`
compatibility facade do not import FastMCP, argparse, or `albumentationsx_mcp.adapters`. Assert each CLI adapter module
stays below its documented size ceiling: 650 lines for leaf adapters, 250 for composition modules, and 120 for the
facade.

- [ ] **Step 2: Add an Unreleased changelog entry**

Document the internal CLI adapter extraction and canonical CLI snapshot. Do not claim a new command, changed output,
or release.

- [ ] **Step 3: Run focused and full verification**

Run:

```bash
uv run pytest -q tests/test_cli_adapters.py tests/test_cli_contract_snapshot.py tests/test_architecture_boundaries.py
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv run python scripts/check_contract_snapshots.py
uv run python scripts/check_release_readiness.py --tag v1.19.0
git diff --exit-code -- tests/fixtures/snapshots/cli_contract.json \
  tests/fixtures/snapshots/mcp_contract.json tests/fixtures/snapshots/output_contracts.json
```

- [ ] **Step 4: Mark the plan complete and commit**

```bash
git add CHANGELOG.md tests/test_architecture_boundaries.py \
  docs/superpowers/plans/2026-07-15-cli-adapter-extraction.md
git commit -m "docs: complete CLI adapter extraction"
```
