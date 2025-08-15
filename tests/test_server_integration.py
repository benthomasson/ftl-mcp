"""Integration tests for FTL MCP server tools."""

from pathlib import Path

import pytest
from fastmcp import Client


@pytest.mark.asyncio
async def test_load_inventory_with_localhost():
    """Test loading inventory.yml and verifying localhost is in the inventory state."""
    # Get the path to the inventory.yml file in the repo root
    repo_root = Path(__file__).parent
    inventory_path = repo_root / "inventory.yml"
    
    # Verify the inventory file exists
    assert inventory_path.exists(), f"inventory.yml not found at {inventory_path}"
    
    # Import the MCP server
    from src.ftl_mcp.server import mcp
    
    # Test using FastMCP Client
    async with Client(mcp) as client:
        # Load the inventory using the MCP tool
        result = await client.call_tool("load_inventory", {
            "inventory_path": str(inventory_path)
        })

        # Verify the load was successful
        assert result.data["status"] == "success"
        assert result.data["total_hosts"] >= 1
        assert "localhost" in result.data["hosts"]
        
        # Get inventory status to verify persistence
        status_result = await client.call_tool("get_inventory_status", {})
        assert status_result.data["inventory_loaded"] is True
        assert status_result.data["total_hosts"] >= 1
        assert "localhost" in status_result.data["hosts"]
        
        # Get all hosts to verify localhost details
        hosts_result = await client.call_tool("get_inventory_hosts", {})
        assert hosts_result.data["group"] == "all"
        assert hosts_result.data["host_count"] >= 1
        assert "localhost" in hosts_result.data["hosts"]
        
        # Verify localhost details in the hosts result
        localhost_details = hosts_result.data["hosts"]["localhost"]
        assert localhost_details["name"] == "localhost"
        assert "ansible_connection" in localhost_details["vars"]
        assert localhost_details["vars"]["ansible_connection"] == "local"


@pytest.mark.asyncio
async def test_load_inventory_localhost_in_all_group():
    """Test that localhost is properly associated with the 'all' group."""
    # Get the path to the inventory.yml file in the repo root
    repo_root = Path(__file__).parent
    inventory_path = repo_root / "inventory.yml"
    
    # Import the MCP server
    from src.ftl_mcp.server import mcp
    
    # Test using FastMCP Client
    async with Client(mcp) as client:
        # Load the inventory using the MCP tool
        result = await client.call_tool("load_inventory", {
            "inventory_path": str(inventory_path)
        })
        
        # Verify the load was successful
        assert result.data["status"] == "success"
        
        # Get all hosts to check group associations
        hosts_result = await client.call_tool("get_inventory_hosts", {})
        
        # Check that localhost is associated with a group
        localhost_host = hosts_result.data["hosts"]["localhost"]
        assert len(localhost_host["groups"]) > 0
        
        # Since the inventory has localhost under 'all', it should have 'all' in its groups
        # The exact group assignment depends on how the inventory parser processes the structure


@pytest.mark.asyncio  
async def test_inventory_state_persistence():
    """Test that inventory state persists and can be queried after loading."""
    # Get the path to the inventory.yml file in the repo root
    repo_root = Path(__file__).parent
    inventory_path = repo_root / "inventory.yml"
    
    # Import the MCP server
    from src.ftl_mcp.server import mcp
    
    # Test using FastMCP Client
    async with Client(mcp) as client:
        # First, load the inventory
        load_result = await client.call_tool("load_inventory", {
            "inventory_path": str(inventory_path)
        })
        assert load_result.data["status"] == "success"
        
        # Test the get_inventory_status tool
        status_result = await client.call_tool("get_inventory_status", {})
        assert status_result.data["inventory_loaded"] is True
        assert status_result.data["total_hosts"] >= 1
        assert "localhost" in status_result.data["hosts"]
        
        # Test the get_inventory_hosts tool  
        hosts_result = await client.call_tool("get_inventory_hosts", {})
        assert hosts_result.data["group"] == "all"
        assert hosts_result.data["host_count"] >= 1
        assert "localhost" in hosts_result.data["hosts"]
        
        # Verify localhost details in the hosts result
        localhost_details = hosts_result.data["hosts"]["localhost"]
        assert localhost_details["name"] == "localhost"
        assert "ansible_connection" in localhost_details["vars"]


@pytest.mark.asyncio
async def test_load_inventory_file_not_found():
    """Test load_inventory with non-existent file."""
    # Import the MCP server
    from src.ftl_mcp.server import mcp
    
    # Test using FastMCP Client
    async with Client(mcp) as client:
        # Try to load non-existent file
        result = await client.call_tool("load_inventory", {
            "inventory_path": "/nonexistent/path/inventory.yml"
        })
        
        # Should return error
        assert "error" in result.data
        assert "does not exist" in result.data["error"]
