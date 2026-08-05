# Public Proof and First-Preview Feedback Loop Implementation Plan

> **For agentic workers:** Use test-driven development and execute every task in order. Keep each task in its own
> commit, except generated evidence and status updates that must be committed only after their validators exist.

**Goal:** Publish verifiable `1.20.0 -> 1.21.0` machine proof, restore merge-safe evidence provenance, bound HTTP test
cleanup, and give first-time users a privacy-safe feedback path without adding telemetry or MCP surface area.

**Architecture:** Bind generated evidence to source-equivalent Git trees and public workflow metadata using validated
structured sidecars. Keep network/GitHub collection in scripts and workflows, pure validation in package/domain code,
and host-specific behavior out of the MCP server. Treat the issue tracker as an explicit user-operated adapter.

**Tech Stack:** Python 3.10+, pytest, Ruff, ty, uv, Git, GitHub CLI, GitHub Actions, JSON, YAML.

---

## Task 0: Repair Merge-Safe Profile Evidence Provenance

**Files:**
- Modify: `scripts/check_host_profile_conformance.py`
- Modify: `tests/test_host_profile_conformance.py`
- Later regenerate: `docs/host-evidence/profile-conformance-2026-08-04.json`

- [x] Add failing tests for a schema-v3 relevant-tree digest, equivalent non-ancestor commits, an unavailable recorded
  revision, malformed digests, and real relevant-source drift.
- [x] Implement canonical Git-tree hashing with bounded subprocesses and strict parser validation.
- [x] Preserve schema-v2 ancestry validation; validate schema-v3 by current/source tree equivalence.
- [x] Run `uv run pytest tests/test_host_profile_conformance.py -q` and Ruff on the changed files.
- [x] Commit the validator implementation and refresh evidence from the committed relevant tree.

## Task 1: Produce The Public Published-Upgrade Run

**External operations:**
- Dispatch `.github/workflows/published-upgrade-proof.yml` on `main` with `from_version=1.20.0` and
  `to_version=1.21.0`.
- Wait for completion and inspect the public run metadata and job log.
- Download the `published-upgrade-proof` artifact to a new private temporary directory.

- [x] Require a successful workflow conclusion and the expected repository, workflow, inputs, and head branch.
- [x] Parse the downloaded report with the repository's strict upgrade-proof parser.
- [x] Compare the downloaded report byte-for-byte with the current committed report; replace the committed report only
  if the successful public run legitimately differs.
- [x] Compute and record the artifact report SHA-256 and public run URL.
- [x] Do not commit temporary archives, API responses, logs, or local paths.

## Task 2: Bind Evidence To Public Workflow Provenance

**Files:**
- Modify: `src/albumentationsx_mcp/lifecycle.py`
- Modify: `scripts/export_lifecycle_status.py`
- Create: `scripts/export_published_upgrade_provenance.py`
- Modify: `.github/workflows/published-upgrade-proof.yml`
- Modify: `tests/test_lifecycle.py`
- Modify: `tests/test_published_upgrade_workflow.py`
- Create: `tests/test_published_upgrade_provenance.py`
- Create: `docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-04.provenance.json`
- Regenerate: `docs/STATUS.md`

- [x] Write failing pure tests for the provenance schema, canonical serialization, expected GitHub identity, run URL,
  workflow ref, head SHA, artifact member, retention, and evidence SHA mismatch.
- [x] Implement a small provenance exporter that derives the run URL and hashes the exact evidence bytes.
- [x] Extend the lifecycle evidence loader to require and bind the sidecar; keep path and stable-file protections.
- [x] Render the public run link, finite-retention caveat, and non-attestation statement in generated status Markdown.
- [x] Extend the workflow to generate report and provenance files and upload both under the same retained artifact.
- [x] Build the committed sidecar from the observed public run, validate it, and regenerate `docs/STATUS.md`.
- [x] Run focused lifecycle/workflow/provenance tests, Ruff, and `ty`.
- [x] Commit public workflow provenance and generated status together.

## Task 3: Hard-Bound HTTP Harness Shutdown

**Files:**
- Modify: `tests/support/mcp_http.py`
- Modify: `tests/test_mcp_http_harness.py`

- [x] Add a regression test whose serve task suppresses its first cancellation until an independent release signal.
- [x] Prove the existing cleanup exceeds the configured bound, with a safety release preventing the test from hanging.
- [x] Replace unbounded cancellation gathers with two bounded `asyncio.wait` phases and eventual-result consumption.
- [x] Preserve startup errors, caller errors, shutdown errors, listener closure, and clean cooperative teardown.
- [x] Run the harness and full Streamable HTTP conformance tests.
- [x] Commit the watchdog fix separately.

## Task 4: Add The Privacy-Safe First-Preview Feedback Funnel

**Files:**
- Create: `docs/FIRST_PREVIEW_FEEDBACK.md`
- Modify: `.github/ISSUE_TEMPLATE/workflow-feedback.yml`
- Modify: `README.md`
- Modify: `docs/FIRST_10_MINUTES.md`
- Modify: `docs/INDEX.md`
- Modify: `tests/test_community_intake.py`

- [x] Add failing tests for discoverable links, lifecycle fields, required privacy attestation, and prohibited-data copy.
- [x] Add one concise, copy-ready `render -> reject -> adjust -> accept` report template.
- [x] Refine the existing issue form instead of creating a duplicate intake channel.
- [x] Link the funnel from the first-preview journey, README, and docs index without making README heavy.
- [x] Run focused docs/intake tests and Ruff.
- [x] Commit the voluntary feedback funnel separately.

## Task 5: Refresh Evidence, Verify, Publish, And Merge

**Files:**
- Regenerate: `docs/host-evidence/profile-conformance-2026-08-04.json`
- Modify if required: `.gitattributes`
- Regenerate if required: `docs/STATUS.md`

- [ ] Generate profile evidence from the final relevant source tree and verify its schema-v3 digest.
- [ ] Run focused tests, full `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run ty check`.
- [ ] Run contract snapshot freshness, release readiness, golden MCP flows, and privacy scans used by CI.
- [ ] Review the complete diff for overclaims, local paths, secrets, generated drift, and accidental public-surface changes.
- [ ] Push `codex/public-proof-feedback-loop`, open a ready PR, wait for every required check, and squash-merge it.
- [ ] Pull merged `main` and rerun the post-squash profile-provenance regression.
- [ ] Do not tag or release unless a package runtime contract changes unexpectedly.

## Success Criteria

1. The baseline profile-evidence test passes both before and after squash merge.
2. A public successful GitHub run proves `1.20.0 -> 1.21.0`, and committed bytes match its downloaded report SHA-256.
3. `docs/STATUS.md` links the run and accurately states the trust and retention boundaries.
4. HTTP harness cleanup has no unbounded await after the configured shutdown timeout.
5. A first-time user can submit a useful, redacted lifecycle report in one GitHub issue without any automatic data
   collection.
