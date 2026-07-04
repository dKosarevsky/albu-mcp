# Beta Import Instructions

```bash
albu-mcp beta response-validate --input filled-beta-response.json --format json
albu-mcp beta response-import-dir --input-dir docs/beta-loop --format json
albu-mcp beta report --format json
albu-mcp trust dashboard --format markdown
```
