# V1.4 Host Smoke Workflow Design

AlbumentationsX MCP already exposes a diagnostics report and a client smoke playbook, but host agents still have to stitch
several outputs together before deciding whether preview rendering is safe. v1.4 adds one machine-readable host smoke
tool that combines environment diagnostics, recipe recommendation, pipeline validation, and a preview request template
without reading user datasets or rendering previews.

## Goal

Give MCP hosts a single safe preflight call that answers: "Can I proceed to a small preview, and exactly what request
shape should I use next?"

## Approach

Use a small orchestration layer instead of expanding `DiagnosticsService` into a workflow engine. The new
`host_smoke.py` module owns typed smoke models and report assembly. `server.py` remains a FastMCP adapter: it calls
`diagnose_environment`, `recommend_recipe`, and `validate_pipeline`, then passes those typed results to the host smoke
builder.

Alternatives considered:

- Extend `diagnose_environment`: simpler surface, but it would mix environment checks with recipe and validation workflow
  state.
- Add a full preview-running smoke: more realistic, but it would read user image paths and create artifacts, which is too
  risky for a default preflight.
- Add a new read-only `run_host_smoke_check` tool: best fit because it is explicit, typed, safe, and leaves actual preview
  rendering as the next deliberate host step.

## Public Contract

`run_host_smoke_check` accepts:

- `include_write_probe: bool = true`
- `task: str = "classification"`
- `intensity: "low" | "medium" | "high" = "low"`
- `targets: list[str] | null = null`

It returns `HostSmokeReport`:

- `status`: `ok`, `warning`, or `error`
- `preview_ready`: true only when diagnostics is `ok` and validation is valid
- `checks`: ordered smoke checks for diagnostics, recipe recommendation, pipeline validation, and preview template
- `diagnostics`: the full `DiagnosticsReport`
- `next_actions`: concise host instructions
- `remediation_actions`: diagnostics remediation actions copied through for automation
- `preview_request_template`: a safe `render_preview_batch` request template when `preview_ready` is true, otherwise null

The preview template uses one placeholder path under the first configured allowed root, `variants_per_image=1`,
`seed=0`, and `max_side=512`. It includes the validated recipe pipeline, but it does not inspect files or write preview
artifacts.

## Error Handling

Diagnostics warnings or errors block `preview_ready` and preserve structured remediation actions. Recipe and validation
checks are reported separately so hosts can distinguish setup problems from pipeline contract problems. Unknown fields in
the report remain forbidden through the shared `StrictModel` base.

## Testing

Tests are added before production code:

- unit tests for a ready report and a diagnostics-blocked report;
- server and stdio tests for the new tool name;
- MCP contract snapshot update for the public surface change;
- output contract snapshots for representative ready and blocked smoke reports;
- golden MCP eval coverage that calls the tool through stdio and asserts the preview template contract.

## Release

This changes the public MCP tool surface and output contracts, so it ships as `v1.4.0` after local verification, GitHub CI,
PyPI publication, post-release smoke, and MCP Registry metadata publication succeed.
