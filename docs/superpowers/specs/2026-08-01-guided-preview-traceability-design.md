# Guided First Preview And Variant Traceability Design

**Date:** 2026-08-01
**Status:** Approved for implementation

## Problem

AlbumentationsX MCP can already inspect a dataset, recommend and validate a pipeline, render preview artifacts, and
guide a review loop. A new user must nevertheless coordinate at least four tools before seeing the first contact sheet:
`plan_dataset_onboarding`, `build_review_packet`, `validate_preview_request`, and `render_preview_batch`. This increases
host-planning failures and makes the first successful result depend on whether the model follows every intermediate
gate.

Preview manifests currently record the requested pipeline and deterministic seeds, but not the transforms that were
actually applied to each variant or their sampled parameters. Consequently, an agent cannot answer a concrete review
question such as "why is image 8 too noisy?" from stored evidence. It can only infer a likely cause from the requested
pipeline.

The next increment should make the safe first preview a single use case and make every newly rendered variant
inspectable without coupling application logic to FastMCP.

## Goals

1. Render a bounded, validated first preview through one MCP tool.
2. Reuse existing onboarding, recipe, validation, path-policy, rendering, and artifact components.
3. Record the transforms and sampled parameters actually applied to each rendered variant.
4. Expose one read-only tool for retrieving a single variant trace.
5. Preserve existing tools, profiles, manifests, artifact URIs, and rendering behavior.
6. Keep domain and application code independent of FastMCP.

## Non-goals

- Uploading images or accepting arbitrary URLs.
- Hosting the local filesystem server as a public remote endpoint.
- Building the separate public demo runtime or adding `remotes` to `server.json`.
- Parsing Python pipeline source.
- Automatically deciding that a transform caused a semantic failure.
- Storing full displacement maps, image arrays, masks, or other large binary values in manifests.
- Changing the default `full` capability profile.

## Chosen Approach

Add an application-level orchestration service and keep MCP handlers as thin adapters. The service calls existing
components directly rather than invoking one MCP tool from another. This preserves transport independence, makes every
gate unit-testable, and keeps one production path for onboarding, validation, and rendering.

The alternatives were rejected for the following reasons:

- an MCP-level macro would couple business flow to FastMCP registration and error semantics;
- adding onboarding behavior to `render_preview_batch` would mix planning and rendering and change an established
  public contract.

## Architecture

### Guided preview use case

Add `GuidedPreviewService` as an application service. It receives explicit collaborators for path policy, pipeline
validation, preview rendering, and recipe construction. It does not read environment variables, construct stores, or
depend on FastMCP.

The input contract contains:

- `dataset_path`;
- `task`, defaulting to `classification`;
- `intensity`, defaulting to `low`;
- optional target names;
- `max_images`, constrained to 1 through 8.

The first preview always renders one variant per sampled image with seed `0`. Callers that need more variants continue
with the existing adjustment and rendering tools after reviewing the first contact sheet.

The result contract contains:

- a stable status of `rendered` or `blocked`;
- the onboarding report and validation report;
- the normalized preview request when one could be built;
- the `PreviewResult` when rendering succeeded;
- a direct reference to the contact sheet when rendering succeeded;
- trace availability and agent-legible next actions.

Blocked results are normal structured results. They do not write a run directory. Unexpected renderer failures retain
the existing all-or-nothing cleanup behavior and propagate through the current MCP error mapping.

### Applied-transform capture

`PipelineService.build_pipeline` enables AlbumentationsX `Compose(save_applied_params=True)`. This is preferred over
replacing `Compose` with `ReplayCompose`: the installed AlbumentationsX API exposes applied parameters directly while
retaining current `strict`, shape-checking, target, and seed behavior.

After each transform call, `PreviewService` reads `applied_transforms` from the result and creates one variant trace:

- `image_index` and `variant_index`;
- source path and rendered artifact URI;
- effective seed;
- ordered applied transforms;
- JSON-safe sampled parameters.

Trace serialization accepts JSON primitives, paths, mappings, sequences, NumPy scalars, and arrays. Small arrays are
serialized as values. Large arrays are represented by shape, dtype, element count, and SHA-256 digest. This keeps the
trace useful and reproducible without embedding generated fields or pixels. Every trace and parameter collection has
an explicit size and depth bound; values beyond the bound use the same structural summary.

The manifest receives an additive top-level `variant_traces` array and a trace count in `summary`. Existing readers
continue to ignore unknown fields.

### Trace query

Add an application function that reads a manifest through `ArtifactStore`, validates the requested non-negative image
and variant indexes, and returns a typed result:

- `available=true` with the matching trace for new runs;
- `available=false` with a stable explanation for legacy manifests that have no `variant_traces` field;
- a deterministic validation error when the manifest supports traces but the requested variant does not exist.

The query never reads arbitrary paths and never trusts a path supplied by the caller.

### MCP surface

Add two tools:

- `run_first_preview` in the `dataset` and `full` profiles;
- `trace_preview_variant` in the `review`, `dataset`, and `full` profiles.

`run_first_preview` is registered by the dataset adapter and delegates to `GuidedPreviewService`.
`trace_preview_variant` is registered by the preview adapter and delegates to the trace query. The canonical adapter
surface remains the only source of profile membership and ordering.

No existing tool is renamed or removed. The `core` profile remains read-only and preview-free.

## Data Flow

1. The MCP adapter validates the small tool input schema and calls `GuidedPreviewService`.
2. The service builds the existing dataset onboarding report with `max_images <= 8`.
3. If onboarding is not preview-ready, the service returns `blocked` without allocating a run.
4. The service extracts the generated request template and validates it through `PreviewRequestValidator`.
5. If validation fails, the service returns `blocked` without allocating a run.
6. The service converts the normalized request to `PreviewRequest` and calls `PreviewService`.
7. `PreviewService` renders each image, captures applied parameters, writes images and contact sheets, then completes
   the manifest and run index using the existing all-or-cleanup run lifecycle.
8. The adapter returns the typed result, including the contact-sheet artifact reference and trace lookup instruction.
9. A later `trace_preview_variant` call reads only the controlled manifest and returns one matching trace.

## Error Handling And Safety

- Dataset paths must remain within configured allowed roots.
- The use case caps work at eight inputs, one variant per input, and the existing maximum image side.
- Onboarding and validation failures are structured `blocked` results, not partial previews.
- Rendering exceptions remove the newly allocated run directory as they do today.
- Trace serialization is deterministic, bounded, and does not include image or annotation payloads.
- A missing legacy trace is reported as unavailable, not treated as a corrupt run.
- A malformed `variant_traces` field is treated as a corrupt manifest and fails explicitly.
- Artifact lookup continues to use run IDs and manifest-recorded URIs protected by `ArtifactStore`.

## Compatibility

All existing request and result schemas remain unchanged. `PreviewResult` remains compatible; guided-preview fields use
a new result model. Manifest changes are additive. Existing manifests and runs remain listable, comparable, readable,
and deletable.

Enabling applied-parameter capture must not change output determinism for a fixed pipeline and seed. A regression test
compares rendered bytes before and after instrumentation for representative transforms.

The full profile gains two tools. Focused profile counts and public-surface snapshots are updated intentionally. CLI,
MCPB, Registry identity, transport defaults, and package entrypoints remain unchanged.

## Testing

1. Unit-test `GuidedPreviewService` for successful rendering and every blocked gate.
2. Prove blocked flows allocate no run and write no artifact.
3. Parameterize trace normalization across primitives, paths, mappings, NumPy values, small arrays, large arrays,
   excessive depth, and excessive collection size.
4. Verify transform traces for deterministic geometric and pixel transforms.
5. Verify identical fixed-seed image bytes after applied-parameter instrumentation.
6. Verify annotation-aware previews still render and record observations.
7. Verify trace lookup for new manifests, legacy manifests, malformed traces, and unknown indexes.
8. Update profile membership, registration order, schema snapshots, and diagnostics expectations.
9. Add a stdio integration test that calls `run_first_preview`, reads the generated contact sheet resource, and calls
   `trace_preview_variant`.
10. Run the full pytest suite, Ruff lint and format checks, ty, package build, and wheel smoke.

## Delivery

1. Add typed trace models, bounded normalization, and applied-parameter manifest capture.
2. Add trace lookup and the `trace_preview_variant` MCP tool.
3. Add `GuidedPreviewService` and the `run_first_preview` MCP tool.
4. Update profile contracts, workflow documentation, README, and changelog.
5. Run full verification, independent review, and merge through a pull request.

The public demo runtime is intentionally a later design and release. It will reuse the guided use case against curated
fixtures, but it will have a separate composition root, a smaller public surface, no caller-controlled filesystem
inputs, and deployment-specific abuse controls.

## Success Criteria

- A host can produce a validated first contact sheet with one tool call.
- A blocked first preview creates no run or artifact.
- Every newly rendered variant records the transforms and sampled parameters that were actually applied.
- A host can retrieve one variant trace without reading arbitrary files.
- Large generated values cannot cause unbounded manifest growth.
- Existing preview and annotation workflows remain deterministic and compatible.
- The profile contract and stdio integration tests cover both new tools.
- No public remote endpoint is advertised before the separate demo-runtime safety design is implemented and verified.
