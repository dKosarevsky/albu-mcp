# Host Profile Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce repeatable machine proof and real-host evidence for all four capability profiles, the resource fallback, and one Claude Desktop feedback loop.

**Architecture:** Keep protocol conformance, host observation, and generated-fixture workflow evidence independent. Add two focused developer scripts: one generates immutable operator inputs, while the other probes the exact current checkout over MCP stdio. Host receipts are committed only after observed runs and never inferred from generated files.

**Tech Stack:** Python 3.10-3.13, MCP Python SDK, argparse, dataclasses, JSON/TOML text generation, pytest parameterization, Ruff, ty, Codex CLI, Claude Desktop.

---

## File Map

- Create `scripts/export_host_profile_acceptance_packet.py`: validate bounded local inputs and generate host configs,
  prompts, and a pending receipt.
- Create `scripts/check_host_profile_conformance.py`: run exact-surface, smoke, and fallback parity checks over stdio.
- Create `tests/test_host_profile_acceptance_packet.py`: packet validation and deterministic artifact tests.
- Create `tests/test_host_profile_conformance.py`: parameterized protocol-result and CLI tests.
- Create `docs/host-evidence/profile-conformance-2026-07-15.json`: sanitized machine proof from the current revision.
- Create `docs/host-evidence/codex-profile-matrix-2026-07-15.md`: real Codex observation receipt.
- Create `docs/host-evidence/claude-desktop-profile-review-2026-07-15.md`: real Claude Desktop profile and review-loop receipt.
- Modify `docs/HOST_MANUAL_RUNS.json` and generated host reports only if the observed Claude Desktop replay closes an
  existing pending evidence kind.

### Task 1: Commit Approved Design and Plan

**Files:**
- Create: `docs/superpowers/specs/2026-07-15-host-profile-acceptance-design.md`
- Create: `docs/superpowers/plans/2026-07-15-host-profile-acceptance.md`

- [ ] **Step 1: Review the spec for placeholders and evidence-class contradictions**

Run:

```bash
rg -n "T[B]D|T[O]DO|generated.*adoption|machine.*host evidence" \
  docs/superpowers/specs/2026-07-15-host-profile-acceptance-design.md \
  docs/superpowers/plans/2026-07-15-host-profile-acceptance.md
```

Expected: no placeholders; every generated-fixture statement explicitly rejects adoption classification.

- [ ] **Step 2: Commit the approved documents**

```bash
git add docs/superpowers/specs/2026-07-15-host-profile-acceptance-design.md \
  docs/superpowers/plans/2026-07-15-host-profile-acceptance.md
git commit -m "docs: design host profile acceptance"
```

### Task 2: Generate a Bounded Host Acceptance Packet

**Files:**
- Create: `scripts/export_host_profile_acceptance_packet.py`
- Create: `tests/test_host_profile_acceptance_packet.py`

- [ ] **Step 1: Write failing validation and artifact tests**

Define a fixture that creates an executable `python`, an allowed root containing `sample-grid.png`, and a separate
artifact root. Assert that `build_host_profile_acceptance_artifacts()` returns exactly:

```python
{
    "README.md",
    "codex-config.toml",
    "claude-desktop-config.json",
    "profile-matrix-prompt.md",
    "claude-review-loop-prompt.md",
    "receipt-template.json",
}
```

Parameterize invalid inputs for relative paths, a missing executable, a sample outside the allowed root, an artifact
root inside the allowed root, an empty revision, and an unsupported host.

- [ ] **Step 2: Run the tests and confirm the missing module failure**

```bash
uv run pytest tests/test_host_profile_acceptance_packet.py -q
```

Expected: collection fails because `scripts.export_host_profile_acceptance_packet` does not exist.

- [ ] **Step 3: Implement the packet builder and thin CLI**

Use this public shape:

```python
@dataclass(frozen=True)
class HostProfileAcceptancePacketConfig:
    server_python: Path
    source_revision: str
    allowed_root: Path
    artifact_root: Path
    sample_image: Path
    run_date: str
    hosts: tuple[str, ...] = ("Codex", "Claude Desktop")


def build_host_profile_acceptance_artifacts(
    config: HostProfileAcceptancePacketConfig,
) -> dict[str, str]: ...
```

Generate four servers in deterministic `CapabilityProfile` order. Put `--capability-profile <value>` in every server
argument list. The receipt template must use `pending` for every host/profile/fallback/workflow status and include the
non-fabrication classification.

- [ ] **Step 4: Run focused quality checks**

```bash
uv run pytest tests/test_host_profile_acceptance_packet.py -q
uv run ruff check scripts/export_host_profile_acceptance_packet.py tests/test_host_profile_acceptance_packet.py
uv run ty check scripts/export_host_profile_acceptance_packet.py
```

Expected: all pass.

- [ ] **Step 5: Commit the packet generator**

```bash
git add scripts/export_host_profile_acceptance_packet.py tests/test_host_profile_acceptance_packet.py
git commit -m "feat: generate host profile acceptance packet"
```

### Task 3: Add Exact MCP Stdio Conformance

**Files:**
- Create: `scripts/check_host_profile_conformance.py`
- Create: `tests/test_host_profile_conformance.py`

- [ ] **Step 1: Write failing parameterized profile tests**

For every `CapabilityProfile`, start the current interpreter with `-m albumentationsx_mcp`, list tools, resources,
resource templates, and prompts, and compare them to `surface_for_profile(profile)`. Assert:

```python
assert result["surface_matches"] is True
assert result["smoke_ok"] is True
assert result["fallback_matches_resource"] is True
assert result["preview_ready"] is (profile is not CapabilityProfile.CORE)
```

Also test deterministic JSON rendering and a nonzero CLI exit when any profile result is failed.

- [ ] **Step 2: Run the tests and confirm the missing module failure**

```bash
uv run pytest tests/test_host_profile_conformance.py -q
```

Expected: collection fails because `scripts.check_host_profile_conformance` does not exist.

- [ ] **Step 3: Implement the asynchronous checker**

Use `StdioServerParameters`, `stdio_client`, and `ClientSession`. Call:

```python
await session.initialize()
await session.list_tools()
await session.list_resources()
await session.list_resource_templates()
await session.list_prompts()
await session.call_tool("run_host_smoke_check", {"include_write_probe": False})
await session.read_resource(AnyUrl("albumentationsx://examples/client-smoke"))
await session.call_tool("get_workflow_example", {"example_id": "client-smoke"})
```

Return only names, counts, booleans, profile, revision, and failure messages. Do not emit absolute roots or image data.

- [ ] **Step 4: Run focused and full protocol tests**

```bash
uv run pytest tests/test_host_profile_conformance.py tests/test_mcp_profiles.py tests/test_mcp_stdio.py -q
uv run ruff check scripts/check_host_profile_conformance.py tests/test_host_profile_conformance.py
uv run ty check scripts/check_host_profile_conformance.py
```

Expected: all pass.

- [ ] **Step 5: Commit protocol conformance**

```bash
git add scripts/check_host_profile_conformance.py tests/test_host_profile_conformance.py
git commit -m "test: add profile stdio conformance report"
```

### Task 4: Produce Machine Proof and Real Codex Evidence

**Files:**
- Create: `docs/host-evidence/profile-conformance-2026-07-15.json`
- Create: `docs/host-evidence/codex-profile-matrix-2026-07-15.md`

- [ ] **Step 1: Generate a local sample and operator packet**

```bash
uv run python scripts/export_host_profile_acceptance_packet.py \
  --server-python "$PWD/.venv/bin/python" \
  --revision "$(git rev-parse HEAD)" \
  --allowed-root "$PWD/docs/assets/demo/inputs" \
  --artifact-root /private/tmp/albu-host-profile-artifacts \
  --sample-image "$PWD/docs/assets/demo/inputs/sample-grid.png" \
  --date 2026-07-15 \
  --output-dir /private/tmp/albu-host-profile-packet
```

Expected: six files written; no canonical evidence changed.

- [ ] **Step 2: Run and commit machine conformance**

```bash
uv run python scripts/check_host_profile_conformance.py \
  --revision "$(git rev-parse HEAD)" \
  --allowed-root "$PWD/docs/assets/demo/inputs" \
  --artifact-root /private/tmp/albu-host-profile-conformance \
  --output docs/host-evidence/profile-conformance-2026-07-15.json
```

Expected: status `passed` for all four profiles.

- [ ] **Step 3: Run real Codex with ephemeral profile overrides**

Load the four entries from the generated Codex config as `-c` overrides, run `codex exec --ephemeral --sandbox
read-only`, and use `profile-matrix-prompt.md`. Save the final response outside the repository before sanitizing it.

- [ ] **Step 4: Write the Codex receipt from observed output**

The receipt must state exact passed/blocked observations, source revision, fallback path, and evidence class. It must not
include tokens, user paths, raw logs, or adoption claims.

- [ ] **Step 5: Commit machine and Codex evidence**

```bash
git add docs/host-evidence/profile-conformance-2026-07-15.json \
  docs/host-evidence/codex-profile-matrix-2026-07-15.md
git commit -m "docs: record profile conformance and Codex acceptance"
```

### Task 5: Complete Claude Desktop Review and Integrate

**Files:**
- Create: `docs/host-evidence/claude-desktop-profile-review-2026-07-15.md`
- Modify when justified: `docs/HOST_MANUAL_RUNS.json`
- Modify when justified: generated host evidence reports

- [ ] **Step 1: Install the generated temporary Claude Desktop configuration**

Merge the four generated `mcpServers` entries without removing unrelated user servers, restart Claude Desktop, and
verify all four servers initialize from the exact current checkout.

- [ ] **Step 2: Execute the profile matrix and fallback prompt**

Use `profile-matrix-prompt.md`. Record direct resource success or the observed resource-blind failure followed by a
successful `get_workflow_example` call for each profile.

- [ ] **Step 3: Execute the reviewer-observed feedback loop**

Use `claude-review-loop-prompt.md`, inspect both contact sheets, reject the baseline as `too_noisy:high`, and accept the
candidate only if it remains recognizable. A model-generated acceptance without reviewer inspection is insufficient.

- [ ] **Step 4: Verify and record the artifacts**

Check manifests and PNG hashes under the bounded artifact root. Write the privacy-safe Claude Desktop receipt. Update
the existing first-10-minutes record only if the observed flow satisfies every existing replay gate.

- [ ] **Step 5: Run final verification**

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/check_contract_snapshots.py
uv run python scripts/run_golden_evals.py --work-dir /private/tmp/albu-host-profile-golden
```

Expected: all pass.

- [ ] **Step 6: Review, push, and merge**

Request an independent diff review, fix validated findings, push `codex/host-profile-validation`, create a PR, wait for
CI, and merge only after every required check passes. Do not create a tag or release.
