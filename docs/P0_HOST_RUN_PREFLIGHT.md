# P0 Host Run Preflight

Preflight status: `passed`

Record real host UI evidence only after this preflight passes.

## Checks

| Check | Status | Message |
| --- | --- | --- |
| package_import | passed | albumentationsx_mcp imports |
| allowed_root | passed | docs/assets/demo/inputs |
| artifact_root | passed | docs/assets/demo |
| demo_assets | passed | demo asset bundle is valid |
| host_prompts | passed | examples/first_10_minutes_prompt.md has required host prompts |
| run_session_doc | passed | docs/P0_HOST_RUN_SESSION.md is ready |
| manual_records | passed | docs/HOST_MANUAL_RUNS.json is valid (0 manual UI records) |

## Next Commands

- `uv run python scripts/check_p0_host_run_preflight.py`
- `uv run python scripts/export_p0_host_run_session.py --output docs/P0_HOST_RUN_SESSION.md`
- `uv run python scripts/record_host_manual_run.py ...`
