# Public Proof and First-Preview Feedback Loop Design

## Context

AlbumentationsX MCP `1.21.0` has executable Streamable HTTP and published-upgrade probes, but the public upgrade
workflow has not yet produced a run that users can inspect. The generated status page therefore describes the probe
without binding the committed evidence bytes to one public GitHub Actions run.

The previous host-profile evidence also exposed a provenance weakness after PR #88 was squash-merged. Its
`source_revision` names the feature-branch commit that generated the report. That commit is no longer an ancestor of
`main`, even though the relevant source tree is byte-for-byte equivalent. A fresh clone may not contain the detached
commit at all. Commit ancestry alone is therefore the wrong identity for generated evidence that must survive squash
merges.

The loopback HTTP test harness has one related reliability gap: after its graceful shutdown timeout it cancels tasks
and awaits them without another bound. A cancellation-resistant task can consume the entire CI job timeout. Finally,
the project has detailed beta-response machinery but no short, obvious path for a first-time user to report the most
valuable product signal: `render -> reject -> adjust -> accept`.

## Decision

Implement one evidence-to-feedback hardening iteration with five outcomes:

1. Run the existing public `Published upgrade proof` workflow for `1.20.0 -> 1.21.0`.
2. Download its artifact, verify its SHA-256, and commit a bounded provenance sidecar tied to the public run.
3. Regenerate `docs/STATUS.md` from validated evidence and provenance, using deliberately limited claims.
4. Give the test-only HTTP harness a second bounded cancellation phase.
5. Add a privacy-safe first-preview feedback document and refine the existing issue form; add no telemetry and no
   new MCP tool.

Before those outcomes, repair host-profile provenance so the repository returns to a green baseline and future
evidence remains valid after squash merges.

## Goals

- Make current machine proof independently traceable to a public workflow run and exact committed bytes.
- Keep all status claims reproducible from committed structured inputs.
- Preserve strict drift detection while allowing source-equivalent squash commits.
- Bound the harness's own shutdown waits even when cancellation is delayed.
- Reduce first-user feedback friction without collecting data automatically.
- Preserve the current MCP surface, privacy model, and release compatibility.

## Non-Goals

- Do not claim the GitHub artifact is permanently retained or cryptographically attested.
- Do not claim Claude Desktop, Codex, Cursor, or real-user acceptance from machine-only evidence.
- Do not deploy a hosted image-processing MCP server.
- Do not add analytics, callbacks, identifiers, or background uploads.
- Do not add a feedback MCP tool when a standard GitHub issue is sufficient.
- Do not publish a package release for test, evidence, and documentation-only changes.

## Architecture

### Merge-Safe Host-Profile Provenance

Host-profile evidence moves to schema version 3 and adds `relevant_tree_sha256`. The digest is computed from a
canonical stream of Git tree entries under the profile-conformance source boundary: path, mode, object type, and blob
object id. It excludes commit metadata and is therefore stable when a feature branch is squash-merged without changing
the relevant files.

Generation still requires `--revision` to resolve to the exact repository `HEAD`. Validation follows these rules:

1. validate the revision and digest formats;
2. compute the relevant-tree digest for current `HEAD` and require an exact match;
3. if the recorded revision is available, require its relevant-tree digest to match the report too;
4. if the recorded revision is unavailable, accept schema-v3 evidence only when the current-tree digest matches;
5. keep the existing ancestry-and-diff validation for legacy schema-v2 evidence.

This preserves fail-closed drift detection and keeps old reports understandable. The digest is a reproducibility
binding, not a signature or external attestation.

### Public Upgrade Evidence Provenance

The successful workflow artifact remains the canonical generated upgrade report. A separate JSON sidecar records only
public, bounded metadata:

- schema version and evidence classification;
- GitHub repository, workflow path, run id, run URL, and run head SHA;
- artifact name and retention caveat;
- committed evidence path and SHA-256;
- verification timestamp/date and overall status.

A pure validator loads the report and sidecar, rejects malformed or unexpected repository/workflow identities, and
requires the sidecar digest to match the committed report bytes. The generated status page links the public run and
states that the committed bytes were verified against the downloaded artifact. It also states that GitHub artifact
retention is finite and that this is not cryptographic attestation.

The workflow is extended to emit the provenance metadata needed by future runs next to the report, so a maintainer no
longer has to reconstruct it manually. The first sidecar is built from `gh run view` output and the downloaded artifact.

### Bounded HTTP Harness Shutdown

The loopback harness uses two explicit shutdown phases with the configured timeout as the budget for each:

1. request graceful Uvicorn shutdown and wait without cancelling the serve task;
2. on timeout or caller cancellation, cancel lifespan and serve tasks, then wait once more with a hard bound.

No timeout branch performs an unbounded `gather`. Completed task exceptions are consumed; still-pending tasks receive a
done callback that consumes their eventual result. The context manager closes its listener in all cases and reports a
stable timeout error only when the user block itself completed successfully, preserving the original exception
otherwise.

This bounds the harness's cleanup coroutine. Python cannot forcibly terminate arbitrary code that suppresses task
cancellation; process-level CI timeout remains the outer containment boundary for such code. The focused regression
test uses a task that delays cancellation long enough to prove the harness returns before that task is released.

### First-Preview Feedback Funnel

Add a short `docs/FIRST_PREVIEW_FEEDBACK.md` page linked from the first-preview journey and documentation index. It
contains a copy-ready, redacted report template for:

- user goal and host;
- initial render outcome;
- rejection reason;
- adjustment requested;
- accepted outcome or unresolved blocker;
- optional safe artifact references and exported report.

The existing `Preview workflow feedback` issue form is updated to mirror this lifecycle and adds a required privacy
attestation. The form explicitly forbids images, absolute local paths, secrets, personal data, and proprietary dataset
details unless the reporter has intentionally made them public. Submission remains fully voluntary.

## Error Handling and Trust Boundaries

- Tree-digest computation fails closed on Git errors, malformed entries, unsupported object types, or timeouts.
- A sidecar cannot validate a different evidence file, repository, workflow, run URL, head SHA, or artifact name.
- Status generation fails rather than rendering unverified provenance.
- Artifact-retention limitations are visible in generated status text.
- HTTP cleanup errors never replace an exception raised by the caller's test body.
- Feedback documentation never implies that local files are uploaded by the server.

## Verification

- Focused, parameterized tests for schema-v3 generation, equivalent non-ancestor trees, unavailable revisions, and
  relevant-source drift.
- Focused tests for provenance parsing, evidence digest mismatch, unexpected GitHub identity, and status rendering.
- A cancellation-delay regression test proving the HTTP harness returns within its bounded cleanup budget.
- Static tests for issue-form privacy requirements and feedback-document links.
- Regenerated host-profile evidence and generated status output.
- Full `pytest`, Ruff lint/format, `ty`, contract snapshots, release readiness, and golden MCP flows.
- Public workflow success plus local SHA-256 comparison of the downloaded and committed evidence.

## Release Policy

The iteration changes no MCP tool, resource, prompt, package runtime contract, or dependency. Merge it without a tag or
PyPI release. If implementation uncovers a user-facing runtime defect, fix and release that defect separately under
the existing compatibility policy.
