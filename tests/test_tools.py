"""Tests for MCP tools."""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import os

from ftl_mcp.tools import (
    get_current_time,
    calculate_speed,
    list_directory,
)


def test_get_current_time():
    """Test get_current_time tool."""
    result = get_current_time()
    
    # Should be a valid ISO format timestamp
    assert isinstance(result, str)
    # Should be parseable as datetime
    parsed_time = datetime.fromisoformat(result)
    assert isinstance(parsed_time, datetime)


def test_calculate_speed_normal():
    """Test calculate_speed with normal values."""
    result = calculate_speed(100.0, 2.0)
    
    expected = {
        "distance_km": 100.0,
        "time_hours": 2.0,
        "speed_kmh": 50.0,
        "speed_ms": 50.0 / 3.6,
        "is_faster_than_light": False
    }
    
    assert result == expected


def test_calculate_speed_faster_than_light():
    """Test calculate_speed with faster than light values."""
    # Use a very small time to create unrealistic speed
    result = calculate_speed(1000000000.0, 0.000001)
    
    assert result["is_faster_than_light"] is True
    assert result["speed_ms"] > 299792458  # Speed of light


def test_calculate_speed_zero_time():
    """Test calculate_speed with zero time raises error."""
    with pytest.raises(ValueError, match="Time must be greater than zero"):
        calculate_speed(100.0, 0.0)


def test_calculate_speed_negative_time():
    """Test calculate_speed with negative time raises error."""
    with pytest.raises(ValueError, match="Time must be greater than zero"):
        calculate_speed(100.0, -1.0)


def test_list_directory_current():
    """Test list_directory with current directory."""
    result = list_directory(".")
    
    assert isinstance(result, dict)
    assert "error" not in result
    assert "path" in result
    assert "item_count" in result
    assert "items" in result
    assert isinstance(result["items"], list)


def test_list_directory_with_temp_dir():
    """Test list_directory with a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test files
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        test_subdir = Path(temp_dir) / "subdir"
        test_subdir.mkdir()
        
        result = list_directory(temp_dir)
        
        assert isinstance(result, dict)
        assert "error" not in result
        assert result["item_count"] == 2
        
        items = result["items"]
        names = [item["name"] for item in items]
        assert "test.txt" in names
        assert "subdir" in names
        
        # Check file vs directory types
        for item in items:
            if item["name"] == "test.txt":
                assert item["type"] == "file"
                assert item["size"] is not None
            elif item["name"] == "subdir":
                assert item["type"] == "directory"
                assert item["size"] is None


def test_list_directory_nonexistent():
    """Test list_directory with non-existent path."""
    result = list_directory("/path/that/does/not/exist")
    
    assert isinstance(result, dict)
    assert "error" in result
    assert "does not exist" in result["error"]


def test_list_directory_not_directory():
    """Test list_directory with a file path instead of directory."""
    with tempfile.NamedTemporaryFile() as temp_file:
        result = list_directory(temp_file.name)
        
        assert isinstance(result, dict)
        assert "error" in result
        assert "not a directory" in result["error"]