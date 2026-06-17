# Claude Code Preview Command

Import AlbumentationsX MCP with bounded local preview access:

```bash
claude mcp add-json albumentationsx \
  '{"type":"stdio","command":"uvx","args":["--from","albumentationsx-mcp","albumentationsx-mcp","--allowed-root","/absolute/path/to/images","--artifact-root","/absolute/path/to/albu-artifacts"]}'
```

After import, run the shared first preview workflow in [first_preview_workflow.md](first_preview_workflow.md).
