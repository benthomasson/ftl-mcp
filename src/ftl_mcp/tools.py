"""Core tool functions for FTL MCP server."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any


def get_current_time() -> str:
    """Get the current time in ISO format."""
    return datetime.now().isoformat()


def read_file(path: str) -> str:
    """Read the contents of a file.

    Args:
        path: Path to the file to read (URI format: file:///absolute/path)

    Returns:
        File contents as string
    """
    try:
        # Handle both regular paths and file:// URIs
        if path.startswith("file://"):
            # Extract the actual file path from the URI
            actual_path = path.replace("file://", "", 1)
        else:
            actual_path = path

        file_path = Path(actual_path)
        if not file_path.exists():
            return f"Error: File does not exist: {actual_path}"

        if not file_path.is_file():
            return f"Error: Path is not a file: {actual_path}"

        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {str(e)}"


def list_environment_variables() -> dict[str, str]:
    """List all environment variables."""
    return dict(os.environ)
