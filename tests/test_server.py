from albumentationsx_mcp.server import create_mcp_server


def test_create_mcp_server_registers_fastmcp_instance() -> None:
    server = create_mcp_server()

    assert server.name == "AlbumentationsX MCP"


def test_server_exposes_documented_tool_names() -> None:
    server = create_mcp_server()

    tool_names = set(server._tool_manager._tools)

    assert {
        "search_transforms",
        "get_transform_schema",
        "validate_pipeline",
        "recommend_pipeline",
        "adjust_pipeline",
        "render_preview",
        "export_pipeline",
    }.issubset(tool_names)
