"""Tests for MCP tools."""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ftl_mcp.tools import (
    get_current_time,
)


def test_get_current_time():
    """Test get_current_time tool."""
    result = get_current_time()

    # Should be a valid ISO format timestamp
    assert isinstance(result, str)
    # Should be parseable as datetime
    parsed_time = datetime.fromisoformat(result)
    assert isinstance(parsed_time, datetime)