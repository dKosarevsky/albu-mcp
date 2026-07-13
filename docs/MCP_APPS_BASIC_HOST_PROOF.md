# MCP Apps Basic Host Proof

Verification date: `2026-07-13`

This receipt records generated-fixture machine evidence for the interactive preview review surface.
It is not real beta or adoption evidence. It does not claim that a named production host has shipped or enabled MCP
Apps.

## Reference Host

- Repository: `modelcontextprotocol/ext-apps`
- Package: `@modelcontextprotocol/ext-apps` `1.7.4`
- Commit: `ca1d29894fabbd1558885a9ec8620dcb01d7457e`
- Host: the repository's official `examples/basic-host`
- Topology: host on `localhost:8080`, sandbox on `localhost:8081`, and AlbumentationsX MCP on loopback port `3001`

The MCP server used a generated repository fixture under a bounded `--allowed-root` and wrote only to a temporary
`--artifact-root`. The loopback test harness allowed CORS from the one exact basic-host origin. It did not change the
normal stdio product path.

## Reproduction

Build the committed MCP App first:

```bash
npm --prefix mcp-app ci
npm --prefix mcp-app run test
npm --prefix mcp-app run typecheck
npm --prefix mcp-app run build
```

Start the bounded loopback server from this repository:

```bash
uv run python -m scripts.run_mcp_apps_basic_host_harness \
  --allowed-root docs/assets/demo \
  --artifact-root /tmp/albu-mcp-app-proof \
  --allowed-origin http://localhost:8080
```

In a separate checkout of the reference host:

```bash
git clone https://github.com/modelcontextprotocol/ext-apps.git /tmp/mcp-ext-apps
git -C /tmp/mcp-ext-apps checkout ca1d29894fabbd1558885a9ec8620dcb01d7457e
npm --prefix /tmp/mcp-ext-apps ci
npm --prefix /tmp/mcp-ext-apps run build
npm --prefix /tmp/mcp-ext-apps/examples/basic-host run start
```

Open `http://localhost:8080`, select `render_preview_batch`, and use one generated fixture with three variants. The
proof run used `docs/assets/demo/inputs/sample-grid.png`, a Pascal VOC box, `HorizontalFlip`, and `GaussNoise`.

## Observed Results

| Check | Result |
| --- | --- |
| MCP App discovery | The host resolved `ui://albumentationsx/preview-review.html` from render-tool metadata. |
| Resource boundary | The app loaded selected PNGs and contact sheets through verified `artifact://` reads. |
| Media | Selected images decoded at `160 x 120`; the contact sheet decoded at `320 x 240`. |
| Review controls | Image/variant navigation, image/overlay mode, eight server tags, severity, note, and accept controls rendered. |
| Draft state | A per-variant issue draft survived navigation and did not appear on another variant. |
| Feedback write | `record_preview_feedback` persisted `too_noisy:medium` for variant 2. |
| Accept write | `record_preview_feedback` persisted `accepted=true` for variant 3. |
| Fullscreen | The host switched the app from inline to fullscreen and back. |
| Desktop | Viewer and feedback columns met at one boundary without overlap. |
| Mobile | At `390 x 844`, feedback stacked below the viewer with no horizontal overflow. |
| Console | No warnings or errors were emitted after the successful final host connection. |
| Network | Empty MCP Apps CSP, the self-contained bundle check, and loopback-only server logs showed no external application dependency. |

The persisted server record for the final run contained exactly one rejected variant with `too_noisy:medium` and one
accepted variant. Source paths were absent from app labels; the UI displayed ordinal labels and a shortened run id.

## Evidence Classification

| Evidence | Status | Supports | Does not support |
| --- | --- | --- | --- |
| TypeScript, Python, package, and stdio tests | Passed | Contracts, integrity checks, fallback behavior | Visual behavior in a host |
| Official basic-host generated fixture | Passed on 2026-07-13 | MCP Apps handshake, rendering, interaction, persistence, responsive layout | Real user value, production-host support, adoption |
| External MCP Apps host review | Not recorded | A named host and reviewer workflow when completed | Any claim before a dated record exists |
| Beta/adoption evidence | Not recorded for this UI | Product value and repeated real use when supplied | Generated fixtures or maintainer rehearsals |

Screenshots were not committed as evidence: the run used a generated fixture, and the structured receipt plus
reproducible harness is more stable than host-specific screenshot composition. Existing manual host and beta records
remain governed by `docs/HOST_MANUAL_RUNS.json` and the evidence commands.
