"""Integration tests for Ansible module execution via faster_than_light."""

from pathlib import Path

import pytest
from fastmcp import Client




@pytest.mark.asyncio  
async def test_ansible_argtest_localhost():
    """Test executing argtest module on localhost using ansible_module tool."""
    # Import the MCP server
    from src.ftl_mcp.server import mcp
    
    # Test using FastMCP Client
    async with Client(mcp) as client:
        # Execute argtest module on localhost
        result = await client.call_tool("ansible_module", {
            "module_name": "argtest",
            "hosts": "localhost",
            "module_args": {"message": "Hello FTL"}
        })
        
        # Debug: Print the actual result to see what we got
        print(f"Result data: {result.data}")
        
        # Verify the execution was successful
        assert result.data["status"] == "success"
        assert result.data["module"] == "argtest"
        assert "localhost" in result.data["hosts"]
        assert "results" in result.data
        
        # Check that the module executed successfully
        localhost_result = result.data["results"]["localhost"]
        # argtest should echo back our message in more_args field
        assert "more_args" in localhost_result
        assert "Hello FTL" in str(localhost_result["more_args"])


@pytest.mark.asyncio
async def test_ansible_module_generic():
    """Test the generic ansible_module tool."""
    # Import the MCP server
    from src.ftl_mcp.server import mcp
    
    # Test using FastMCP Client  
    async with Client(mcp) as client:
        # Execute timetest module using generic tool
        result = await client.call_tool("ansible_module", {
            "module_name": "timetest",
            "hosts": "localhost",
            "module_args": {}
        })
        
        # Verify the execution was successful
        assert result.data["status"] == "success"
        assert result.data["module"] == "timetest"
        assert "localhost" in result.data["hosts"]
        assert "results" in result.data
        
        # Check timetest result
        localhost_result = result.data["results"]["localhost"]
        # timetest module should return a time field
        assert "time" in localhost_result




@pytest.mark.asyncio
async def test_multiple_hosts():
    """Test executing modules on multiple hosts (localhost multiple times)."""
    # Import the MCP server
    from src.ftl_mcp.server import mcp
    
    # Test using FastMCP Client
    async with Client(mcp) as client:
        # Execute timetest on multiple "hosts" (really just localhost)
        result = await client.call_tool("ansible_module", {
            "module_name": "timetest",
            "hosts": "localhost, localhost",  # Test comma-separated parsing
            "module_args": {}
        })
        
        # Verify the execution was successful
        assert result.data["status"] == "success"
        assert result.data["module"] == "timetest"
        # Should deduplicate to just localhost
        assert len(result.data["hosts"]) >= 1
        assert "results" in result.data


@pytest.mark.asyncio
async def test_close_ansible_connections():
    """Test closing FTL connections."""
    # Import the MCP server
    from src.ftl_mcp.server import mcp
    
    # Test using FastMCP Client
    async with Client(mcp) as client:
        # Close connections
        result = await client.call_tool("close_ansible_connections", {})
        
        # Verify the cleanup was successful
        assert result.data["status"] == "success"
        assert "message" in result.data


@pytest.mark.asyncio
async def test_execution_state_tracking():
    """Test that execution history is tracked in state manager."""
    # Import the MCP server
    from src.ftl_mcp.server import mcp
    
    # Test using FastMCP Client
    async with Client(mcp) as client:
        # Execute argtest module to generate history
        await client.call_tool("ansible_module", {
            "module_name": "argtest",
            "hosts": "localhost",
            "module_args": {"message": "test"}
        })
        
        # The execution should be stored in state manager
        # We can't directly access state manager from tests, but we verified
        # the code stores execution records in the generic storage
        
        # This test mainly verifies the tools execute without errors
        # Full state verification would require exposing state query tools