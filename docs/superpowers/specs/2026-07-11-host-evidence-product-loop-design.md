# Codex Host Evidence Product Loop Design

## Goal

Turn the 2026-07-11 Codex plugin replay into an honest evidence-to-product iteration: preserve a sanitized host
acceptance receipt, fix the two workflow gaps observed during that replay, and publish the already implemented
unreleased tool surface as one coherent minor release.

## Observed Evidence

An interactive Codex session loaded the personal AlbumentationsX MCP plugin, completed `run_host_smoke_check`, and
executed the generated-fixture first-ten-minutes workflow through preview, adjustment, comparison, acceptance, and
export. The run exposed three concrete facts:

1. `plan_dataset_onboarding` rejected a direct supported image path and required a retry with its parent directory.
2. The feedback catalog had reduction tags for excessive exposure, but no structured way to request stronger
   brightness and contrast variation when a candidate looked unchanged.
3. The stable `1.15.0` plugin pin did not expose tools already present on `main`, including `build_review_packet`.

This is real host acceptance evidence over a generated fixture. It is not beta-user evidence, production adoption,
or proof that the workflow generalizes to private datasets.

## Selected Scope

### Evidence boundary

Commit a human-readable receipt and the two small contact sheets needed to audit the replay. Canonical host records
will mark only the Codex lanes as passed and link repository-relative artifacts. Session logs, absolute local paths,
and generated fixture inputs remain uncommitted.

### Single-image onboarding

Treat `dataset_path` as an image source rather than a directory-only field. An allowed, existing supported image is
its own one-item inventory; its parent is the read-only context root for annotation and dataset-structure discovery.
Unsupported files receive a dedicated actionable error. Directory behavior and filesystem boundaries remain
unchanged.

### Weak-exposure feedback

Add `exposure_too_weak` as a specific structured tag. It raises only brightness/contrast probability and ranges,
using bounded severity profiles. Safety-reduction tags (`too_dark`, `too_bright`, `color_shift`, and
`object_unrecognizable`) take precedence, so contradictory feedback can never strengthen exposure.

The adjustment remains deterministic:

| Severity | Minimum probability | Range growth | Default symmetric limits |
| --- | ---: | ---: | ---: |
| low | 0.40 | 1.25x | 0.20 |
| medium | 0.65 | 1.50x | 0.30 |
| high | 1.00 | 2.00x | 0.40 |

Brightness and contrast limits are capped at `[-1.0, 1.0]`. Existing non-exposure transforms are not strengthened.

### Release boundary

Release `1.16.0` because the public MCP tool surface and feedback vocabulary expand compatibly. Synchronize
`pyproject.toml`, `uv.lock`, `.mcp.json`, `.codex-plugin/plugin.json`, and the changelog. The tagged release remains
the trigger for trusted PyPI publication and MCP Registry refresh.

## Architecture

- `onboarding.py` owns image-source classification and reuses the existing path policy, inventory, annotation, and
  preview-template services.
- `feedback.py` owns severity semantics; `presets.py` applies the bounded transform mutation.
- `advisor.py`, `review_agent.py`, and `recipes.py` expose the same tag consistently to MCP hosts and natural-language
  review flows.
- Canonical evidence stays in `docs/HOST_MANUAL_RUNS.json`; generated summaries continue to come from existing
  exporters and freshness checks.
- Release metadata remains guarded by existing project, plugin, build, and registry validators.

## Testing

- Parameterized onboarding tests cover supported images, unsupported files, root policy, exact request paths, and
  annotation context.
- Parameterized feedback tests cover all severities, absent and existing ranges, upper bounds, immutability, and
  safety-conflict precedence.
- Review-agent and recipe tests lock natural-language interpretation and catalog discoverability.
- Evidence schema/freshness tests validate the receipt links and regenerated reports.
- Full pytest, Ruff, formatting, ty, build, golden evals, MCP smoke, plugin validation, and release readiness must pass
  before merge and tagging.

## Non-Goals

- Claiming external beta feedback or real-dataset adoption.
- Automatically scanning sibling images when a single image was requested.
- Adding a generic “make everything stronger” feedback tag.
- Changing allowed roots, artifact permissions, or host configuration automatically.
- Backporting the new tool surface into the already published `1.15.0` artifact.
