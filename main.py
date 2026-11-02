
import random
from fastmcp import FastMCP

mcp = FastMCP("Simple Calculator Server")

@mcp.tool()
def add_numbers(a: float, b: float) -> float:
    """Add two numbers and return their sum."""
    return a + b

@mcp.tool()
def generate_random_number(min_value: int, max_value: int) -> int:
    """Generate a random integer between minimum and maximum."""
    if min_value > max_value:
        raise ValueError("Minimum cannot exceed maximum.")
    return random.randint(min_value, max_value)

@mcp.resource("resource://server-info")
def get_server_info() -> str:
    """Return information about this MCP server."""
    return "Simple Calculator Remote MCP Server - Version 1.0"

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000
    )
