"""FTL MCP server implementation using fastmcp."""

from fastmcp import FastMCP

from .tools import (
    get_current_time as _get_current_time,
    calculate_speed as _calculate_speed,
    list_directory as _list_directory,
    read_file as _read_file,
    list_environment_variables as _list_environment_variables,
)

# Create the MCP server
mcp = FastMCP("ftl-mcp")


@mcp.tool()
def get_current_time() -> str:
    """Get the current time in ISO format."""
    return _get_current_time()


@mcp.tool()
def calculate_speed(distance: float, time: float) -> dict[str, str]:
    """Calculate speed given distance and time.
    
    Args:
        distance: Distance in kilometers
        time: Time in hours
        
    Returns:
        Dictionary with speed calculations
    """
    return _calculate_speed(distance, time)


@mcp.tool()
def list_directory(path: str = ".") -> dict[str, str]:
    """List contents of a directory.
    
    Args:
        path: Directory path to list (defaults to current directory)
        
    Returns:
        Dictionary with directory information
    """
    return _list_directory(path)


@mcp.resource("file://{path}")
def read_file(path: str) -> str:
    """Read the contents of a file.
    
    Args:
        path: Path to the file to read
        
    Returns:
        File contents as string
    """
    return _read_file(path)


@mcp.resource("env://")
def list_environment_variables() -> dict[str, str]:
    """List all environment variables."""
    return _list_environment_variables()


def main():
    """Run the FTL MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()