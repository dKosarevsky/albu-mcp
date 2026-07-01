# Real Evidence Intake Sprint

## Goal

Turn the remaining blocked release gates into a clear operator intake flow without fabricating host or beta evidence.

## Constraints

- Keep all new commands report-only unless the existing import commands are invoked explicitly.
- Do not create tags, releases, uploads, or evidence records from generated fixtures.
- Use test-first changes and keep each implementation point in a separate commit.

## Plan

1. Add a manual evidence runbook command that links command-center, packet generation, import checklist, validation, import, privacy checks, trust dashboard, and RC candidate review.
2. Add a replay fixture pack command that writes local demo material for a real host run while labeling it as non-evidence.
3. Add beta response template export for all three validation workflows.
4. Add a trust gate transition report comparing before and after records.
5. Add a release owner packet that states current status, required attachments, safe commands, and commands blocked until go.

## Governed Loop

After the five points are implemented, run the existing 100-iteration governor as far as the current evidence gates allow. Stop at the external evidence gate rather than inventing records.
