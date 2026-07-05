# Real Evidence Input Checklist

Use this checklist to unblock `activation real-adoption-cycle` without treating generated artifacts as evidence.

Target time: 10-15 minutes per host/beta participant once the MCP host is available.

## 1. Host Evidence

The current P0 gate requires reviewer-observed runs for both hosts:

- `Codex`
- `Claude Code`

For each host, create a manifest:

```bash
albu-mcp evidence session-manifest \
  --host Codex \
  --date YYYY-MM-DD \
  --reviewer "Release operator" \
  --output-dir docs/operator-packets \
  --format json
```

For `Claude Code`, run the same command with `--host "Claude Code"`.

Edit the generated `*-evidence-session-manifest.json` after the reviewer actually observes the real MCP host UI:

```json
{
  "manifest_status": "filled",
  "status": "passed",
  "evidence": "Reviewer observed the real MCP host UI, listed AlbumentationsX MCP tools/resources, ran run_host_smoke_check, and confirmed preview_ready=true.",
  "artifacts": [
    "docs/operator-evidence/redacted-host-run-notes.md"
  ],
  "commands_used": [
    "run_host_smoke_check",
    "render_preview_batch"
  ],
  "confirm_real_host_observed": true,
  "private_data_included": false
}
```

Keep the existing `host`, `date`, and `reviewer` fields. Do not include private dataset paths, credentials,
unredacted image names, or host screenshots that expose private data.

Validate before import:

```bash
albu-mcp evidence validate-manifest \
  --input docs/operator-packets/codex-evidence-session-manifest.json \
  --format json

albu-mcp evidence proof-runner \
  --input docs/operator-packets/codex-evidence-session-manifest.json \
  --format json
```

Import only after validation passes and the reviewer confirms the run was real:

```bash
albu-mcp evidence import-manifest \
  --input docs/operator-packets/codex-evidence-session-manifest.json \
  --format json

albu-mcp evidence close-host --host Codex --format json
```

Repeat validation and import for `Claude Code`.

## 2. Beta Validation

Fill all three files in `docs/beta-response-templates/`:

- `dataset-health-before-training-beta-response.json`
- `noisy-preview-tuning-beta-response.json`
- `robustness-distortion-variants-beta-response.json`

Each file must keep:

- `private_data_included`: `false`
- `status`: `passed` or `needs_followup`
- `summary`: a concrete redacted participant outcome, not the placeholder text
- `artifact_refs`: only redacted relative references, never private local paths

Use these buckets unless the participant signal clearly points elsewhere:

- `dataset_health_before_training` -> `dataset_quality_gap`
- `noisy_preview_tuning` -> `review_agent_v3_gap`
- `robustness_distortion_variants` -> `workflow_fit_gap`

Validate each filled draft:

```bash
albu-mcp beta response-validate \
  --input docs/beta-response-templates/dataset-health-before-training-beta-response.json \
  --format json
```

Before importing individual records, run the combined import wizard in no-write mode:

```bash
albu-mcp evidence import-wizard \
  --host-manifest docs/operator-packets/codex-evidence-session-manifest.json \
  --host-manifest docs/operator-packets/claude-code-evidence-session-manifest.json \
  --beta-dir docs/beta-response-templates \
  --format json
```

When the wizard reports `ready_to_import`, import the filled host manifests and beta directory:

```bash
albu-mcp evidence import-wizard \
  --host-manifest docs/operator-packets/codex-evidence-session-manifest.json \
  --host-manifest docs/operator-packets/claude-code-evidence-session-manifest.json \
  --beta-dir docs/beta-response-templates \
  --import-ready \
  --format json
```

Alternatively, import the filled beta directory directly:

```bash
albu-mcp beta response-import-dir \
  --input-dir docs/beta-response-templates \
  --format json
```

## 3. Gate Check

After host and beta imports, rerun:

```bash
albu-mcp activation real-adoption-cycle --host Codex --format json
albu-mcp activation evidence-product-loop --host Codex --format json
albu-mcp beta triage --format json
albu-mcp activation first-product-fix --host Codex --format json
albu-mcp activation first-product-fix --host Codex --output-dir docs/first-product-fix --format markdown
albu-mcp activation product-fix-implementation-plan --host Codex --format json
albu-mcp activation product-fix-implementation-plan --host Codex --output-dir docs/product-fix-implementation-plan --format markdown
albu-mcp activation product-fix-execution-guard --host Codex --format json
albu-mcp activation product-fix-execution-guard --host Codex --output-dir docs/product-fix-execution-guard --format markdown
albu-mcp activation product-fix-validation --host Codex --format json
albu-mcp activation product-fix-validation --host Codex --output-dir docs/product-fix-validation --format markdown
albu-mcp activation product-fix-outcome-capture --host Codex --output-dir docs/product-fix-outcome-capture --format markdown
albu-mcp activation product-fix-outcome-import-guard --host Codex --input docs/product-fix-outcome-capture/post-fix-noisy-preview-tuning-beta-response.json --output-dir docs/product-fix-outcome-import-guard --format markdown
albu-mcp activation product-fix-outcome-rehearsal --host Codex --input docs/product-fix-outcome-capture/post-fix-noisy-preview-tuning-beta-response.json --output-dir docs/product-fix-outcome-rehearsal --format markdown
albu-mcp activation product-fix-outcome --host Codex --format json
albu-mcp activation product-fix-outcome --host Codex --output-dir docs/product-fix-outcome --format markdown
```

Only select the first product fix when:

- `cycle_status` is `ready_for_first_product_fix`
- `implementation_allowed` is `true`
- `selector_status` is `ready_for_implementation`
- `selected_fix` is not `null`
- `triage_status` is not `blocked_until_beta_signal`

## Stop Conditions

Stop and do not import if any input contains:

- private dataset paths or credentials
- generated artifacts presented as observed host evidence
- unmodified beta template summaries
- `confirm_real_host_observed=false`
- beta status `blocked` for any required workflow
