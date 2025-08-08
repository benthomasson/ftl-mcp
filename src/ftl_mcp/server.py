"""FTL MCP server implementation using fastmcp."""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("ftl-mcp")


@mcp.tool()
def get_current_time() -> str:
    """Get the current time in ISO format."""
    return datetime.now().isoformat()


@mcp.tool()
def calculate_speed(distance: float, time: float) -> dict[str, Any]:
    """Calculate speed given distance and time.
    
    Args:
        distance: Distance in kilometers
        time: Time in hours
        
    Returns:
        Dictionary with speed calculations
    """
    if time <= 0:
        raise ValueError("Time must be greater than zero")
    
    speed_kmh = distance / time
    speed_ms = speed_kmh / 3.6
    
    return {
        "distance_km": distance,
        "time_hours": time,
        "speed_kmh": speed_kmh,
        "speed_ms": speed_ms,
        "is_faster_than_light": speed_ms > 299792458  # Speed of light in m/s
    }


@mcp.tool()
def list_directory(path: str = ".") -> dict[str, Any]:
    """List contents of a directory.
    
    Args:
        path: Directory path to list (defaults to current directory)
        
    Returns:
        Dictionary with directory information
    """
    try:
        dir_path = Path(path)
        if not dir_path.exists():
            return {"error": f"Path does not exist: {path}"}
        
        if not dir_path.is_dir():
            return {"error": f"Path is not a directory: {path}"}
        
        items = []
        for item in dir_path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
                "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
            })
        
        return {
            "path": str(dir_path.absolute()),
            "item_count": len(items),
            "items": sorted(items, key=lambda x: x["name"])
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.resource("file://{path}")
def read_file(path: str) -> str:
    """Read the contents of a file.
    
    Args:
        path: Path to the file to read
        
    Returns:
        File contents as string
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            return f"Error: File does not exist: {path}"
        
        if not file_path.is_file():
            return f"Error: Path is not a file: {path}"
        
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {str(e)}"


@mcp.resource("env://")
def list_environment_variables() -> dict[str, str]:
    """List all environment variables."""
    return dict(os.environ)


def main():
    """Run the FTL MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()