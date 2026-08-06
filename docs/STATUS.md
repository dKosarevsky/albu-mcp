# Project Lifecycle Status

Release publication, host evidence, and adoption measurement are independent dimensions.

## Release Health

Status: `published`

Version: `1.21.0`

| Channel | Status | URL |
| --- | --- | --- |
| pypi | `published` | https://pypi.org/project/albumentationsx-mcp/1.21.0/ |
| github_release | `published` | https://github.com/dKosarevsky/albu-mcp/releases/tag/v1.21.0 |
| ci | `passed` | https://github.com/dKosarevsky/albu-mcp/actions/runs/30771329949 |
| official_registry | `listed` | https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp |

## Protocol Compatibility Evidence

Status: `passed`

Status basis: Passing published upgrade probe; provenance and scope are reported separately.

Published upgrade: `1.20.0 -> 1.21.0`

Evidence: [privacy-safe machine report](host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-05.json)

Evidence SHA-256: `42580ac9d9893b748cd10e38f73067402e5e3b639dee84a5efefbe706bcac18c`

Provenance: Exact report bytes verified from a downloaded public GitHub Actions artifact. This is not cryptographic attestation.

Public run: [public GitHub Actions run](https://github.com/dKosarevsky/albu-mcp/actions/runs/31049485055)

Run source: `8e185cb32a895a31fe3264b313372058fbfcea49`

Provenance record: [privacy-safe JSON](host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-05.provenance.json)

Artifact retention: `30 days`

Scope: Published-package stdio protocol negotiation and artifact continuity. This is not Streamable HTTP or real-host UI evidence.

## Host Evidence

Status: `partial`

Unresolved observations: `2`

- `manual_host_ui_pending`: At least one supported host lacks passed manual UI evidence.
- `first_10_minutes_replay_pending`: At least one supported host lacks passed First 10 Minutes replay evidence.

## Adoption Experiment

Campaign: `classification-robustness`

Status: `measuring`

Baseline: `2026-07-14`

Measurement due: `2026-07-21`

Post URL: `not_recorded`

Success signal: One voluntary render -> reject -> adjust -> accept report.
