from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Noite integration test server")


@mcp.tool()
def echo(text: str) -> str:
    return f"echo:{text}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
