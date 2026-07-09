# Evidence Import Wizard

Wizard status: `blocked`

Writes records: `false`

Post-import cycle status: `blocked`

## Host Manifests

- `docs/operator-packets/codex-evidence-session-manifest.json`: `blocked`; validation=`template_requires_real_evidence`; manifest=`template`
- `docs/operator-packets/claude-code-evidence-session-manifest.json`: `blocked`; validation=`template_requires_real_evidence`; manifest=`template`

## Host Actions

- `docs/operator-packets/codex-evidence-session-manifest.json`
  - Set manifest_status to filled only after reviewer-observed real MCP host UI evidence exists.
  - Replace TODO evidence with redacted reviewer-observed host UI and first-preview details.
  - Set confirm_real_host_observed to true only after reviewer confirmation.
  - Keep private_data_included false and artifact references privacy-safe.
  - `albu-mcp evidence validate-manifest --input docs/operator-packets/codex-evidence-session-manifest.json --path docs/HOST_MANUAL_RUNS.json --format json`
  - `albu-mcp evidence proof-runner --input docs/operator-packets/codex-evidence-session-manifest.json --path docs/HOST_MANUAL_RUNS.json --beta-records docs/BETA_VALIDATION_RECORDS.json --format json`

- `docs/operator-packets/claude-code-evidence-session-manifest.json`
  - Set manifest_status to filled only after reviewer-observed real MCP host UI evidence exists.
  - Replace TODO evidence with redacted reviewer-observed host UI and first-preview details.
  - Set confirm_real_host_observed to true only after reviewer confirmation.
  - Keep private_data_included false and artifact references privacy-safe.
  - `albu-mcp evidence validate-manifest --input docs/operator-packets/claude-code-evidence-session-manifest.json --path docs/HOST_MANUAL_RUNS.json --format json`
  - `albu-mcp evidence proof-runner --input docs/operator-packets/claude-code-evidence-session-manifest.json --path docs/HOST_MANUAL_RUNS.json --beta-records docs/BETA_VALIDATION_RECORDS.json --format json`

## Beta Drafts

- `docs/beta-response-templates/dataset-health-before-training-beta-response.json`: `ready_to_import`
- `docs/beta-response-templates/noisy-preview-tuning-beta-response.json`: `ready_to_import`
- `docs/beta-response-templates/robustness-distortion-variants-beta-response.json`: `ready_to_import`

## Blocked Reasons

- `host_manifest_not_ready`

## Next Commands

- `Fill reviewer-observed host manifests before import.`

## Non-Fabrication Policy

The wizard validates and imports reviewer-observed host manifests and privacy-safe beta drafts only. It does not create real evidence or infer participant outcomes.
