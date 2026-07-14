# Runtime Architecture Hardening Design

**Date:** 2026-07-14
**Status:** Approved for implementation

## Problem

AlbumentationsX MCP has a stable release pipeline and a broad public contract, but its transport adapters have grown
past a maintainable composition boundary. `server.py` is 1,050 lines and directly registers 44 tools, 20 resources,
and 5 prompts. `cli.py` is 2,782 lines and contains 84 command registrations. The domain modules are mostly independent
of FastMCP already, but the two entrypoint modules combine dependency construction, public schema declaration, command
routing, formatting, and operations-only workflows.

The active documentation also mixes three different states. A public release can be healthy while one optional host
lacks manual evidence and while an adoption campaign is still collecting feedback. Historical RC documents currently
surface those host gaps as `ready_for_v1: false` even though v1.19.0 is published and verified. That makes generated
status documents contradict the actual release lifecycle.

The next increment should restore explicit boundaries without removing public contracts or creating a release spike
during the seven-day `classification-robustness` campaign.

## Goals

1. Make `server.py` a small MCP composition facade while preserving the complete default MCP contract.
2. Make `cli.py` a compatibility facade over focused command registrars while preserving every current command.
3. Separate release health, host evidence, and adoption experiment status in active documentation.
4. Add opt-in capability profiles so hosts can expose a smaller, task-focused tool surface.
5. Provide a tool-based workflow-example fallback for hosts that do not expose MCP resource reads.
6. Enforce adapter and domain boundaries with deterministic tests.
7. Keep all work unreleased until the campaign measurement checkpoint.

## Non-goals

- Removing, renaming, or changing the schema of an existing tool, resource, prompt, CLI command, or response field.
- Changing allowed-root, artifact-root, preview retention, or arbitrary-code-execution safety policy.
- Moving every existing module into a new domain/application directory in one refactor.
- Deleting historical evidence or RC records.
- Making `core`, `review`, or `dataset` the default profile in a minor release.
- Adding runtime telemetry or using campaign traffic as proof of successful product adoption.
- Implementing review-agent or dataset-quality depth without a concrete user signal.

## Architecture

### Compatibility facades

`albumentationsx_mcp.server.create_mcp_server` and the current console entrypoints remain public. `server.py` constructs
settings, artifact storage, and FastMCP, then delegates registration to adapter modules. `cli.py` keeps its existing
imports and entrypoint behavior, then delegates parser construction and command dispatch to CLI adapter modules.

Existing import paths therefore continue to work. Internal movement is covered by contract snapshots rather than by
assuming that a refactor is behavior-preserving.

### MCP adapter package

Create `albumentationsx_mcp.adapters.mcp` with focused registrars:

- `catalog`: transform search, schemas, recipes, and catalog resources;
- `policy`: pipeline validation, recommendation, adjustment, explanation, and export;
- `dataset`: onboarding, dataset quality, review packets, and annotation-aware scoring;
- `preview`: request validation, rendering, comparison, feedback, ranking, and reports;
- `sessions`: tuning sessions, decisions, feedback storage, retention, and cleanup;
- `diagnostics`: capabilities, environment checks, host smoke, and workflow examples;
- `prompts`: the public prompt surface;
- `registration`: ordered composition, duplicate detection, and profile filtering.

Each registrar receives explicit dependencies. It may call existing domain or application functions, but it must not
construct unrelated storage or read process environment variables. `server.py` is the only MCP composition root.

### CLI adapter package

Create `albumentationsx_mcp.adapters.cli` with command groups rather than one module per command:

- `runtime`: server launch, diagnostics, onboarding, and first-preview commands;
- `preview`: preview, review, tuning, dataset, and report commands;
- `evidence`: host evidence, beta intake, product-fix, and trust commands;
- `release`: readiness, distribution, registry, and release-review commands;
- `app`: root parser construction, common options, dispatch, and exit-code translation.

The evidence and release groups remain available in v1.20. They are classified as maintainer operations, isolated from
the user runtime path, and considered for deprecation only through the compatibility policy in a later major release.

### Capability profiles

Add a `CapabilityProfile` value to `ServerSettings`, an optional `--capability-profile` server argument, and an
environment equivalent. The accepted profiles are:

- `core`: discovery, pipeline validation, recommendation, adjustment, explanation, export, diagnostics, and smoke;
- `review`: `core` plus preview rendering, comparison, feedback interpretation, ranking, and preview reports;
- `dataset`: `core` plus onboarding, dataset quality, annotation-aware review, and dataset scoring;
- `full`: every current tool, resource, and prompt plus compatible additions.

`full` remains the default for v1.x. A profile is a filtered view of one canonical registration manifest, not a second
implementation. Every item declares its profiles next to its registration metadata. Resources and prompts are filtered
with the same manifest so hosts never receive a prompt that depends on unavailable tools.

The MCPB and existing install examples keep default behavior. New documentation may recommend `review` for users whose
only goal is the preview-feedback-export loop.

### Resource-read fallback

Move workflow-example content behind one application-level lookup keyed by a closed example identifier. Existing MCP
resources reuse that lookup. Add one compatible `get_workflow_example` tool to the diagnostic group so hosts without
resource-read support can retrieve the same reviewed content.

`run_host_smoke_check` continues to return the first preview request template. Its next-action response should mention
the fallback tool only when an example is useful; the server does not attempt to infer client capabilities.

### Lifecycle truth

Active generated status uses three independent dimensions:

- `release_health`: package, GitHub Release, CI, and Registry publication status;
- `host_evidence`: dated, per-host manual evidence without blocking unrelated supported hosts;
- `adoption_experiment`: campaign identifier, baseline date, measurement date, and voluntary success signal.

The launch kit and active index must not derive release readiness from an optional host subscription. Historical RC
documents remain at their current paths for link compatibility, but active navigation moves them behind an archive
index and each document carries a historical-state banner. No historical record is rewritten to claim evidence that
was not observed.

## Data Flow

1. The process entrypoint parses server settings and validates the selected capability profile.
2. `server.py` builds shared dependencies once and passes them to the MCP registration manifest.
3. The manifest filters registrations by profile and validates unique names and URIs.
4. Focused registrars attach handlers that call existing pure domain/application functions.
5. CLI entrypoints build the same application dependencies and route through command-group adapters.
6. Contract exporters instantiate every profile from the same composition path used in production.

No domain function receives a FastMCP instance, argparse namespace, or environment accessor.

## Error Handling

- An unknown capability profile fails before the MCP server starts and lists the accepted values.
- Duplicate tool names, resource URIs, or prompt names fail registration deterministically.
- A prompt or resource with unavailable profile dependencies fails a profile-consistency test.
- Adapter exceptions continue through the current public error mapping; refactoring must not leak new traceback or
  filesystem details to MCP clients.
- Workflow-example lookup rejects unknown identifiers with a stable list of accepted identifiers.
- Missing historical status inputs produce `unknown` or `not_observed`, never `passed` and never a fabricated zero.

## Compatibility And Migration

The full-profile MCP snapshot before and after extraction must be identical except for the additive
`get_workflow_example` tool and explicitly documented description corrections. Existing output snapshots remain
unchanged unless the resource fallback adds a new optional field.

CLI help and command inventory are captured before extraction and compared after each slice. Console scripts,
`create_mcp_server`, environment defaults, MCPB settings, and `server.json` identity remain unchanged.

Profile defaults may change only in a future major release after host evidence demonstrates that a smaller default is
safe. Operations commands may be deprecated only through the additive migration process in `docs/COMPATIBILITY.md`.

## Testing

1. Snapshot the exact full MCP tool, resource, prompt, description, and input-schema contract.
2. Add parameterized profile tests for membership, dependency closure, uniqueness, and deterministic ordering.
3. Add a CLI command-inventory snapshot and focused parser/dispatch tests for every command group.
4. Add workflow-example parity tests proving tool and resource responses use the same application lookup.
5. Add import-boundary tests preventing domain modules from importing `adapters`, FastMCP, or argparse.
6. Run existing golden MCP evaluations and representative output snapshots against `full` and relevant focused
   profiles.
7. Run the full pytest suite, Ruff lint and format checks, ty, MCP App tests/build, package build, MCPB validation, and
   wheel smoke before merge.

## Delivery Slices

1. **Lifecycle truth:** split active statuses and archive historical RC navigation without runtime changes.
2. **MCP extraction:** introduce MCP registrars and reduce `server.py` while preserving the full snapshot.
3. **CLI extraction:** introduce command groups and reduce `cli.py` while preserving command inventory and outputs.
4. **Profiles and fallback:** add opt-in profiles and the resource-read fallback tool.
5. **Completion:** update compatibility/docs, run independent review, and merge without creating a release tag.

Each slice is a separate commit. A v1.20.0 release decision occurs only after the seven-day campaign report and may add
one evidence-backed product slice without combining unrelated feature work.

## Success Criteria

- `server.py` is a composition facade under 300 lines and contains no individual domain workflow implementation.
- `cli.py` is a compatibility facade under 300 lines and contains no command-specific business logic.
- The `full` profile preserves every existing public contract and remains the default.
- Focused profiles expose only dependency-closed tools, resources, and prompts.
- A resource-blind host can retrieve every reviewed workflow example through one tool.
- Active docs no longer report the published v1 line as unreleased because an optional host lacks evidence.
- Domain modules remain transport-independent under automated import-boundary checks.
- No release is tagged before the campaign measurement checkpoint.
