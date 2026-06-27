# RC Beta Product Growth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current blocked RC state into an operational product-development loop: real-host evidence execution, beta validation intake, product-depth reprioritization, and distribution readiness.

**Architecture:** Keep real host evidence manual-only and auditable through `docs/HOST_MANUAL_RUNS.json`. Add generated operator artifacts and status reports that derive from committed JSON records, never from synthetic claims. Each stage is a small exporter/checker with focused tests and release-readiness wiring.

**Tech Stack:** Python 3.10-3.13, `uv`, `pytest`, `ruff`, `ty`, existing generated-doc freshness checks, JSON record files under `docs/`.

---

### Task 1: RC Host Evidence Operations Pack

**Files:**
- Create: `scripts/export_rc_host_evidence_ops.py`
- Create: `docs/RC_HOST_EVIDENCE_OPS.md`
- Test: `tests/test_rc_host_evidence_ops.py`
- Modify: `scripts/check_release_readiness.py`
- Modify: `tests/test_release_readiness.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing tests**

Add tests that assert:
- the ops pack status is `blocked_until_real_host_runs` while P0 evidence is missing;
- required hosts are `Codex` and `Claude Code`;
- the pack contains `check_p0_host_run_preflight.py`, `verify_host_evidence_import.py`, and `check_v1_rc_cutover_gate.py --require-open`;
- committed `docs/RC_HOST_EVIDENCE_OPS.md` is fresh;
- README links the document.

Run: `uv run pytest tests/test_rc_host_evidence_ops.py -q`
Expected: FAIL with missing module/doc.

- [ ] **Step 2: Implement exporter**

Create `build_rc_host_evidence_ops()` and `render_rc_host_evidence_ops_markdown()` that compose:
- `build_p0_host_evidence_ledger()`;
- `build_v1_rc_cutover_gate()`;
- `build_p0_evidence_regeneration_pack()`.

The exporter must not write `docs/HOST_MANUAL_RUNS.json`.

- [ ] **Step 3: Generate docs and wire freshness**

Run:

```bash
uv run python scripts/export_rc_host_evidence_ops.py --output docs/RC_HOST_EVIDENCE_OPS.md
```

Then add a generated-doc check in `scripts/check_release_readiness.py` and add README links.

- [ ] **Step 4: Verify and commit**

Run:

```bash
uv run pytest tests/test_rc_host_evidence_ops.py tests/test_release_readiness.py -q
uv run ruff check scripts/export_rc_host_evidence_ops.py scripts/check_release_readiness.py tests/test_rc_host_evidence_ops.py tests/test_release_readiness.py
uv run python scripts/check_release_readiness.py
```

Commit: `docs: add rc host evidence ops pack`

### Task 2: Beta Validation Records and Status

**Files:**
- Create: `scripts/validate_beta_validation_records.py`
- Create: `scripts/export_beta_validation_status.py`
- Create: `docs/BETA_VALIDATION_RECORDS.json`
- Create: `docs/BETA_VALIDATION_STATUS.md`
- Test: `tests/test_beta_validation_records.py`
- Modify: `scripts/check_release_readiness.py`
- Modify: `tests/test_release_readiness.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing tests**

Add tests that assert:
- empty beta validation records are valid;
- accepted record fields include `workflow`, `status`, `date`, `summary`, `triage_bucket`, `artifacts`;
- duplicate `(workflow, date, summary)` records are rejected;
- generated beta validation status starts as `manual_beta_required`;
- committed docs are fresh and linked.

Run: `uv run pytest tests/test_beta_validation_records.py -q`
Expected: FAIL with missing modules/docs.

- [ ] **Step 2: Implement validator**

Implement Pydantic models with privacy-preserving fields only:
- `workflow`: `robustness_distortion_variants`, `noisy_preview_tuning`, `dataset_health_before_training`;
- `status`: `passed`, `blocked`, `needs_followup`;
- `triage_bucket`: existing buckets from `docs/BETA_VALIDATION_SPRINT.md`;
- `artifacts`: redacted paths or URLs only.

- [ ] **Step 3: Implement status exporter**

Build status from records:
- `manual_beta_required` until every workflow has at least one record;
- `ready_for_depth_triage` when every workflow has at least one non-blocked attempt;
- table by workflow and triage bucket.

- [ ] **Step 4: Wire release-readiness and commit**

Run:

```bash
uv run python scripts/export_beta_validation_status.py --output docs/BETA_VALIDATION_STATUS.md
uv run pytest tests/test_beta_validation_records.py tests/test_release_readiness.py -q
uv run ruff check scripts/validate_beta_validation_records.py scripts/export_beta_validation_status.py tests/test_beta_validation_records.py
uv run python scripts/check_release_readiness.py
```

Commit: `feat: add beta validation records`

### Task 3: Product Depth Gate

**Files:**
- Create: `scripts/export_product_depth_gate.py`
- Create: `docs/PRODUCT_DEPTH_GATE.md`
- Test: `tests/test_product_depth_gate.py`
- Modify: `scripts/check_release_readiness.py`
- Modify: `tests/test_release_readiness.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing tests**

Add tests that assert:
- gate status is `blocked_by_rc_and_beta_signal` while RC cutover is blocked and beta status is incomplete;
- product-depth work remains `p1_after_p0`;
- output references `PRODUCT_DEPTH_BACKLOG.md`, `BETA_VALIDATION_STATUS.md`, and `V1_RC_CUTOVER_GATE.md`;
- committed doc is fresh and linked.

- [ ] **Step 2: Implement gate exporter**

Compose current RC cutover gate, beta validation status, and product depth backlog. Do not reprioritize backlog unless:
- RC cutover allowed is true;
- beta validation status is `ready_for_depth_triage`.

- [ ] **Step 3: Wire freshness and commit**

Run:

```bash
uv run python scripts/export_product_depth_gate.py --output docs/PRODUCT_DEPTH_GATE.md
uv run pytest tests/test_product_depth_gate.py tests/test_release_readiness.py -q
uv run ruff check scripts/export_product_depth_gate.py tests/test_product_depth_gate.py
uv run python scripts/check_release_readiness.py
```

Commit: `docs: add product depth gate`

### Task 4: Distribution Readiness Pack

**Files:**
- Create: `scripts/export_distribution_readiness_pack.py`
- Create: `docs/DISTRIBUTION_READINESS_PACK.md`
- Test: `tests/test_distribution_readiness_pack.py`
- Modify: `scripts/check_release_readiness.py`
- Modify: `tests/test_release_readiness.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing tests**

Add tests that assert:
- pack status is `blocked_until_rc_cutover`;
- publish commands are listed only as blocked while RC cutover is blocked;
- pack includes post-RC distribution checks for PyPI, GitHub Release, MCP Registry, directory presence, and upstream docs link;
- committed doc is fresh and linked.

- [ ] **Step 2: Implement exporter**

Compose:
- `build_v1_rc_cutover_gate()`;
- existing registry/directory scripts as commands, not live network calls;
- README/upstream docs references.

- [ ] **Step 3: Wire freshness and commit**

Run:

```bash
uv run python scripts/export_distribution_readiness_pack.py --output docs/DISTRIBUTION_READINESS_PACK.md
uv run pytest tests/test_distribution_readiness_pack.py tests/test_release_readiness.py -q
uv run ruff check scripts/export_distribution_readiness_pack.py tests/test_distribution_readiness_pack.py
uv run python scripts/check_release_readiness.py
```

Commit: `docs: add distribution readiness pack`

### Final Verification

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/validate_host_manual_runs.py
uv run python scripts/check_release_readiness.py
uv run python scripts/check_contract_snapshots.py
uv run python scripts/check_demo_assets.py --output-dir docs/assets/demo --check
uv run python scripts/run_golden_evals.py
uv build
```

Expected:
- tests pass;
- release-readiness passes;
- `check_v1_rc_cutover_gate.py --require-open` still exits 1 until real P0 evidence is recorded.
