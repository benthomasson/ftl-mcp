"""Tests for MCP resources."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from ftl_mcp.tools import (
    read_file,
    list_environment_variables,
)


def test_read_file_existing():
    """Test reading an existing file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp_file:
        test_content = "This is test content\nWith multiple lines"
        temp_file.write(test_content)
        temp_file.flush()
        
        try:
            result = read_file(temp_file.name)
            assert result == test_content
        finally:
            os.unlink(temp_file.name)


def test_read_file_nonexistent():
    """Test reading a non-existent file."""
    result = read_file("/path/that/does/not/exist.txt")
    
    assert "Error: File does not exist" in result
    assert "/path/that/does/not/exist.txt" in result


def test_read_file_directory():
    """Test reading a directory instead of a file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        result = read_file(temp_dir)
        
        assert "Error: Path is not a file" in result
        assert temp_dir in result


def test_read_file_permission_error():
    """Test reading a file with permission issues."""
    # Create a temp file and remove read permissions
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp_file:
        temp_file.write("test content")
        temp_file.flush()
        
        try:
            # Remove read permissions
            os.chmod(temp_file.name, 0o000)
            
            result = read_file(temp_file.name)
            assert "Error reading file" in result
        finally:
            # Restore permissions and clean up
            os.chmod(temp_file.name, 0o644)
            os.unlink(temp_file.name)


def test_read_file_unicode():
    """Test reading a file with unicode content."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8") as temp_file:
        test_content = "Unicode content: 🚀 ⚡ 🌟"
        temp_file.write(test_content)
        temp_file.flush()
        
        try:
            result = read_file(temp_file.name)
            assert result == test_content
        finally:
            os.unlink(temp_file.name)


def test_list_environment_variables():
    """Test listing environment variables."""
    result = list_environment_variables()
    
    assert isinstance(result, dict)
    # Should contain at least some standard environment variables
    assert len(result) > 0
    
    # Check that it returns actual environment variables
    for key, value in result.items():
        assert isinstance(key, str)
        assert isinstance(value, str)
        assert os.environ.get(key) == value


def test_list_environment_variables_contains_path():
    """Test that environment variables include PATH."""
    result = list_environment_variables()
    
    # PATH should almost always be present
    assert "PATH" in result
    assert result["PATH"] == os.environ["PATH"]


@patch.dict(os.environ, {"TEST_VAR": "test_value"}, clear=False)
def test_list_environment_variables_with_mock():
    """Test environment variables with a mocked variable."""
    result = list_environment_variables()
    
    assert "TEST_VAR" in result
    assert result["TEST_VAR"] == "test_value"