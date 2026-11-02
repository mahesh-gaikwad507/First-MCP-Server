
import random
from mcp.server.fastmcp import FastMCP

# Initialize MCP Server
mcp = FastMCP("Simple Calculator Server")

# Tool 1: Addition
@mcp.tool()
def add_numbers(a: float, b: float) -> float:
    """Add two numbers and return their sum."""
    return a + b


# Tool 2: Generate Random Number
@mcp.tool()
def generate_random_number(min_value: int, max_value: int) -> int:
    """Generate a random integer between minimum and maximum."""
    if min_value > max_value:
        raise ValueError("Minimum cannot exceed maximum.")

    return random.randint(min_value, max_value)


# Resource: Server Information
@mcp.resource("resource://server-info")
def get_server_info() -> str:
    """Return information about this MCP server."""
    return "Simple Calculator Remote MCP Server - Version 1.0"


# Configure HTTP Server
if __name__ == "__main__":
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 8000

    mcp.run(transport="streamable-http")