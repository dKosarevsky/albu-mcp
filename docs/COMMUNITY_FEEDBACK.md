# Community Feedback

Use GitHub issues to collect reproducible MCP host and preview workflow feedback without exposing private data.

Do not upload private datasets, proprietary training images, credentials, or unredacted private filesystem paths. Prefer
small synthetic images, the committed demo assets in `docs/assets/demo/`, or redacted excerpts from generated reports.

## Issue Templates

- `.github/ISSUE_TEMPLATE/host-acceptance.yml`: real MCP host UI reports for Claude Desktop, Claude Code, Cursor,
  Codex, or another host.
- `.github/ISSUE_TEMPLATE/workflow-feedback.yml`: augmentation review loops such as "example 8 is too noisy" using
  `albumentationsx://examples/distortion-review`, `compare_preview_runs`, and `export_preview_report`.
- `.github/ISSUE_TEMPLATE/feature-request.yml`: new MCP host workflows, tools, resources, prompts, or docs.

## Host Acceptance Reports

Generate a reviewer packet before testing:

```bash
uv run python scripts/export_manual_host_acceptance_packet.py --output /tmp/albu-host-acceptance.md
```

The packet gives host-specific configs, a copyable host prompt, and `record_host_manual_run.py` commands. File an issue
when host behavior is surprising or blocked. Record `docs/HOST_MANUAL_RUNS.json` only after a real UI run is completed.

## Preview Workflow Feedback

Good feedback includes:

- task and target type;
- MCP host and package version;
- workflow path, for example `recommend_pipeline -> render_preview_batch -> adjust_pipeline -> compare_preview_runs`;
- feedback tags such as `too_noisy:high`, `too_blurry`, `too_distorted`, `too_dark`, or `acceptable`;
- safe preview run IDs, synthetic contact sheets, or redacted report excerpts.

Avoid broad requests like "make augmentations better" without a concrete preview artifact, task, and expected behavior.
