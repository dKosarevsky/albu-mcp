# Claude Desktop Host Acceptance Receipt - 2026-07-13

## Scope

This receipt records reviewer-observed Claude Desktop Free installation, MCP discovery, and a real smoke tool call. It
also records a separate protocol replay through the exact installed MCPB command over one generated local fixture. It
does not represent external beta feedback, a production dataset, or adoption evidence.

## Environment

- Host: Claude Desktop `1.20186.1`, Free-plan Chat
- Extension/package version: `1.16.0`
- AlbumentationsX version: `2.3.1`
- Transport: local stdio through the installed UV-based MCPB
- Filesystem scope: one dedicated generated-fixture read root and one dedicated artifact write root
- Retention: 100 preview runs
- Fixture: one generated 160 x 120 RGB image containing a grid, rectangle, circle, and `sample object` label

Account identifiers, raw chat content, and absolute private dataset paths are omitted.

## Observed Claude Desktop Workflow

1. Claude Desktop installed the local MCPB, created its UV environment, and installed the pinned Python package.
2. The reviewer selected the dedicated read and write roots and enabled the extension.
3. The host completed `initialize`, `tools/list`, `prompts/list`, and `resources/list` with successful responses.
4. The model could see the listed MCP tools but reported no model-callable resource reader for
   `albumentationsx://examples/client-smoke`.
5. The model called `run_host_smoke_check` directly. The server returned one successful content block with
   `status=ok`, `preview_ready=true`, valid root access, a successful artifact write probe, and the required public
   tools, prompts, and resources.

The MCP log correlates the observed response with one incoming `tools/call` and one successful result. No MCP error was
recorded.

## Installed-Bundle Preview Replay

The exact server command from the installed extension was exercised over stdio with the same bounded roots:

1. `run_host_smoke_check` returned `preview_ready=true`.
2. Its low-intensity classification template was filled with the generated fixture, one variant, seed `0`, and
   `max_side=512`.
3. `validate_preview_request` returned `valid=true`.
4. `render_preview_batch` created one image, one contact sheet, and one manifest without warnings.
5. Visual inspection confirmed that the contact sheet was readable and correctly framed.

The deterministic low-intensity probabilities did not select an active transform for this single variant, so the
contact sheet bytes matched the input fixture. This run proves the installed bundle's bounded render and artifact path;
it is not evidence of a visible augmentation improvement.

## Artifacts

| Artifact | SHA-256 | Observation |
| --- | --- | --- |
| Generated fixture | `ecfa061227d00fc4f298e7623744e32d23d5258a11ee25375e640f655262270c` | Dedicated local test input. |
| Contact sheet | `ecfa061227d00fc4f298e7623744e32d23d5258a11ee25375e640f655262270c` | One readable 160 x 120 preview; identical to the fixture for this seed. |
| Manifest | `dad9a0473b3226443e61121989441b0a8f0b579ae0dd8f72a7f8bcf0b6a8440f` | One input, two image artifacts, four-transform template, seed `0`, no warnings. |

The contact sheet is byte-identical to the already committed deterministic baseline fixture, so this receipt does not
add a duplicate binary file.

## Product Finding

| Finding | Evidence-backed action |
| --- | --- |
| A host may list MCP resources without exposing resource reads to the model. | Keep the resource as detailed optional documentation, state the fallback in the tool description, and include complete typed workflow guidance in `run_host_smoke_check`. |

No generic resource-reader tool is added because it would duplicate the MCP protocol and create a second source of
truth.

## Privacy And Claim Boundary

This receipt supports Claude Desktop manual-host acceptance and an installed-bundle generated-fixture replay only. A
Claude Desktop first-ten-minutes replay is recorded separately only after the real Desktop UI performs preview
validation and rendering. Claude Code remains blocked, and beta/adoption gates remain governed by separate records.
