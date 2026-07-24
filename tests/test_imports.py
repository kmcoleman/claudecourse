def test_agent_sdk_query_importable():
    from claude_agent_sdk import query  # noqa: F401


def test_mcp_fastmcp_importable():
    # Official MCP SDK path. If this ever moves, the documented fallback is the
    # standalone `fastmcp` package (`from fastmcp import FastMCP`); update the
    # pin and src/meridian_capstone/mcp_server/server.py import together, and
    # record the change here.
    from mcp.server.fastmcp import FastMCP  # noqa: F401


def test_jsonschema_importable():
    import jsonschema  # noqa: F401
