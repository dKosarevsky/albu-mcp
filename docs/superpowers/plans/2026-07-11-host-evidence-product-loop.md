# Codex Host Evidence Product Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the successful Codex generated-fixture replay, fix its two observed workflow gaps, and ship the complete current tool surface as `1.16.0`.

**Architecture:** Keep host evidence, image-source onboarding, feedback semantics, and release metadata in their existing ownership boundaries. Drive each behavior through focused tests, regenerate derived contracts with project exporters, then run the complete release matrix before integration.

**Tech Stack:** Python 3.10+, Pydantic, MCP, AlbumentationsX, pytest, Ruff, ty, uv, GitHub Actions.

---

## File Map

- Create `docs/host-evidence/codex-2026-07-11.md`: sanitized host replay receipt.
- Create `docs/assets/host-evidence/codex-2026-07-11-*.png`: auditable baseline and accepted contact sheets.
- Modify `docs/HOST_MANUAL_RUNS.json` and generated evidence reports: canonical Codex pass records.
- Modify `src/albumentationsx_mcp/onboarding.py`: supported single-image source handling.
- Modify `src/albumentationsx_mcp/feedback.py`: bounded growth semantics for feedback severity.
- Modify `src/albumentationsx_mcp/presets.py`: safe exposure-strength adjustment.
- Modify `src/albumentationsx_mcp/advisor.py`, `review_agent.py`, and `recipes.py`: public tag contract.
- Modify focused tests and contract snapshots: deterministic behavior and public schema.
- Modify public docs and skill: image-or-directory wording and new feedback tag.
- Modify release metadata and changelog: synchronized `1.16.0` release.

### Task 1: Codex Host Acceptance Evidence

- [ ] Write the sanitized receipt with host/session identifiers, MCP run identifiers, observable results, hashes, and an explicit generated-fixture limitation.
- [ ] Copy only the baseline and accepted contact sheets into repository assets.
- [ ] Update the two Codex records in `docs/HOST_MANUAL_RUNS.json` to `passed` with repository-relative artifacts.
- [ ] Regenerate every derived host/P0 report named by release-readiness freshness checks.
- [ ] Run host evidence schema, report, replay, and release-readiness tests.
- [ ] Commit as `docs: record Codex host acceptance replay`.

### Task 2: Single-Image Onboarding

- [ ] Add failing parameterized tests for supported images, unsupported files, exact sample paths, parent annotation context, and path-policy rejection.
- [ ] Run `uv run pytest tests/test_onboarding.py tests/test_review_packet.py -q` and confirm the new tests fail for directory-only behavior.
- [ ] Classify an allowed path as directory, supported image, or unsupported file; use the parent only as metadata context.
- [ ] Update public model/tool wording and remediation text from directory-only to image-source language.
- [ ] Run focused tests, Ruff, and ty; regenerate MCP/output contract snapshots if public descriptions change.
- [ ] Commit as `feat: accept single images in onboarding`.

### Task 3: Weak-Exposure Feedback

- [ ] Add failing parameterized tests for low/medium/high growth, default limits, caps, source immutability, and safety conflicts.
- [ ] Add failing review-agent, advisor, and recipe tests for `exposure_too_weak` discovery and natural-language interpretation.
- [ ] Run focused tests and confirm failures identify the absent contract.
- [ ] Implement `severity_scaled_growth`, bounded exposure mutation, and safety-tag precedence.
- [ ] Expose the tag consistently in the catalog, review guidance, and recipes that contain exposure transforms.
- [ ] Run focused tests, Ruff, ty, and regenerate output contracts.
- [ ] Commit as `feat: tune weak exposure from feedback`.

### Task 4: Public Guidance and Stable Release

- [ ] Update README/usage/install/skill wording only where the changed contracts are user-visible; preserve README size guards.
- [ ] Add `1.16.0` changelog notes and move existing Unreleased entries under the dated release heading.
- [ ] Synchronize `pyproject.toml`, `uv.lock`, `.mcp.json`, and `.codex-plugin/plugin.json` versions.
- [ ] Run documentation, plugin, version, and release-readiness tests.
- [ ] Commit as `release: prepare v1.16.0`.

### Task 5: Verification and Integration

- [ ] Review the complete diff for evidence overclaiming, path-policy regressions, contradictory-feedback behavior, metadata drift, and unrelated churn.
- [ ] Run full pytest, Ruff lint/format, ty, golden evals, build, MCP stdio smoke, plugin validators, and tagged release readiness.
- [ ] Push the branch, open a PR, wait for all required CI checks, and merge through GitHub.
- [ ] Fast-forward local `main`, tag and push `v1.16.0`, then verify GitHub release, trusted PyPI publication, MCP Registry status, and installed personal plugin metadata.
- [ ] Report exact commits, checks, publication state, and the next evidence-backed product direction.
