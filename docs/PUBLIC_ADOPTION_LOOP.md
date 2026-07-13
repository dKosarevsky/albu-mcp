# Public Adoption Loop

Package: `albumentationsx-mcp==1.17.1`
Telemetry policy: No automatic telemetry; collect explicit, privacy-safe feedback only.

## Loop Stages

| Stage | Goal | Channels | Proof | Metric | Next Action |
| --- | --- | --- | --- | --- | --- |
| Discover | Help computer-vision users find the project from trusted public surfaces. | `PyPI`, `Official MCP Registry`, `Glama`, `AlbumentationsX docs` | `server.json`, `README.md`, `docs/ADOPTION_PACKET.md` | A user can find the package, repo, install command, and local privacy model. | Keep package, registry, and docs copy aligned after every release. |
| First Run | Turn discovery into a safe local preview within the first session. | `docs/FIRST_10_MINUTES.md`, `docs/INSTALL.md`, `docs/USAGE.md` | `docs/HOST_PROOF_SPRINT_CHECKLIST.md`, `docs/V1_TRUST_GATES.md` | Host runs `run_host_smoke_check` and renders a contact sheet from allowed roots. | Route setup failures to diagnostics docs and the host-acceptance issue template. |
| Review Decision | Convert subjective preview review into structured, reproducible tuning actions. | `interpret_preview_feedback`, `plan_preview_review`, `record_preview_feedback`, `export_preview_report` | `tests/fixtures/snapshots/output_contracts.json`, `docs/USAGE.md` | User feedback maps to tags, a next tool, and an auditable tuning decision. | Use `interpret_preview_feedback` and `plan_preview_review` before adjustment or export. |
| Feedback Intake | Collect actionable reports without asking users to expose private datasets. | `.github/ISSUE_TEMPLATE/host-acceptance.yml`, `.github/ISSUE_TEMPLATE/workflow-feedback.yml`, `.github/ISSUE_TEMPLATE/dataset-health.yml`, `.github/ISSUE_TEMPLATE/feature-request.yml` | `docs/COMMUNITY_FEEDBACK.md`, `docs/NETWORK_GROWTH_TRACKER.md` | Issues include host, command, sanitized artifact, expected result, and actual result. | Label issues by host, workflow, dataset health, or feature request. |
| Release Response | Close the loop by turning repeated feedback into docs, tests, or releases. | `docs/CHANGELOG.md`, `docs/RELEASE.md`, `docs/V1_RELEASE_TRAIN.md` | `tests/test_golden_evals.py`, `tests/test_output_contract_snapshots.py` | Each repeated issue has a regression test, doc update, or explicit non-goal note. | Run weekly triage, batch low-risk fixes, and publish with release evidence. |

## Weekly Operating Rhythm

- Review new GitHub issues and directory comments with docs/ADOPTION_TRIAGE_REPORT.md.
- Group feedback by host setup, dataset health, review workflow, and export workflow.
- Promote repeated reports into tests, docs, or generated launch assets.
- Regenerate launch, network growth, and adoption loop docs before release candidates.

## Next Checks

- `uv run python scripts/export_public_adoption_loop.py --output docs/PUBLIC_ADOPTION_LOOP.md`
- `uv run python scripts/export_adoption_triage_report.py --output docs/ADOPTION_TRIAGE_REPORT.md`
- `uv run python scripts/export_network_growth_tracker.py --output docs/NETWORK_GROWTH_TRACKER.md`
- `uv run python scripts/export_launch_kit.py --output docs/LAUNCH_KIT.md`
