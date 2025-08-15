"""Tests for playbook generation functionality."""

import pytest
from fastmcp import Client


@pytest.mark.asyncio
async def test_playbook_generation_workflow():
    """Test the complete playbook generation workflow."""
    from src.ftl_mcp.server import mcp
    
    async with Client(mcp) as client:
        # Clear any existing tasks
        await client.call_tool("clear_playbook_tasks", {})
        
        # Execute some test modules to generate tasks
        await client.call_tool("ansible_module", {
            "module_name": "argtest",
            "hosts": "localhost",
            "module_args": {"message": "test setup"}
        })
        
        await client.call_tool("ansible_module", {
            "module_name": "timetest", 
            "hosts": "localhost",
            "module_args": {}
        })
        
        # Get the recorded tasks
        tasks_result = await client.call_tool("get_playbook_tasks", {})
        
        # Verify tasks were recorded
        assert "tasks" in tasks_result.data
        assert "summary" in tasks_result.data
        assert tasks_result.data["summary"]["total_tasks"] == 2
        assert tasks_result.data["summary"]["successful_tasks"] == 2
        assert "localhost" in tasks_result.data["summary"]["unique_hosts"]
        assert "argtest" in tasks_result.data["summary"]["unique_modules"]
        assert "timetest" in tasks_result.data["summary"]["unique_modules"]
        
        # Generate playbook
        playbook_result = await client.call_tool("generate_playbook", {
            "playbook_name": "test_playbook",
            "include_failed": False
        })
        
        # Verify playbook generation
        assert playbook_result.data["status"] == "success"
        assert playbook_result.data["playbook_name"] == "test_playbook"
        assert "playbook" in playbook_result.data
        assert "yaml" in playbook_result.data
        assert "metadata" in playbook_result.data
        
        # Check playbook structure
        playbook = playbook_result.data["playbook"]
        assert playbook["name"] == "test_playbook"
        assert playbook["hosts"] == "{{ target_hosts | default('all') }}"
        assert len(playbook["tasks"]) == 2
        
        # Check YAML output
        yaml_output = playbook_result.data["yaml"]
        assert "test_playbook" in yaml_output
        assert "argtest:" in yaml_output
        assert "timetest:" in yaml_output
        
        # Check metadata
        metadata = playbook_result.data["metadata"]
        assert metadata["task_count"] == 2
        assert metadata["host_count"] == 1
        assert "localhost" in metadata["hosts"]
        assert "argtest" in metadata["modules_used"]
        assert "timetest" in metadata["modules_used"]


@pytest.mark.asyncio
async def test_clear_playbook_tasks():
    """Test clearing playbook task history."""
    from src.ftl_mcp.server import mcp
    
    async with Client(mcp) as client:
        # Execute a task to ensure we have something to clear
        await client.call_tool("ansible_module", {
            "module_name": "timetest",
            "hosts": "localhost", 
            "module_args": {}
        })
        
        # Verify task was recorded
        tasks_result = await client.call_tool("get_playbook_tasks", {})
        assert tasks_result.data["summary"]["total_tasks"] > 0
        
        # Clear tasks
        clear_result = await client.call_tool("clear_playbook_tasks", {})
        
        # Verify clear operation
        assert clear_result.data["status"] == "success"
        assert clear_result.data["tasks_cleared"] > 0
        
        # Verify tasks are actually cleared
        tasks_result = await client.call_tool("get_playbook_tasks", {})
        assert tasks_result.data["summary"]["total_tasks"] == 0


@pytest.mark.asyncio
async def test_empty_playbook_generation():
    """Test playbook generation with no recorded tasks."""
    from src.ftl_mcp.server import mcp
    
    async with Client(mcp) as client:
        # Clear all tasks
        await client.call_tool("clear_playbook_tasks", {})
        
        # Try to generate playbook with no tasks
        playbook_result = await client.call_tool("generate_playbook", {
            "playbook_name": "empty_playbook"
        })
        
        # Should return error
        assert "error" in playbook_result.data
        assert "No tasks recorded" in playbook_result.data["error"]


@pytest.mark.asyncio
async def test_playbook_generation_with_include_failed_flag():
    """Test playbook generation with include_failed parameter."""
    from src.ftl_mcp.server import mcp
    
    async with Client(mcp) as client:
        # Clear existing tasks
        await client.call_tool("clear_playbook_tasks", {})
        
        # Execute successful tasks
        await client.call_tool("ansible_module", {
            "module_name": "timetest",
            "hosts": "localhost",
            "module_args": {}
        })
        
        await client.call_tool("ansible_module", {
            "module_name": "argtest",
            "hosts": "localhost", 
            "module_args": {"message": "test"}
        })
        
        # Get all tasks
        tasks_result = await client.call_tool("get_playbook_tasks", {})
        assert tasks_result.data["summary"]["total_tasks"] == 2
        assert tasks_result.data["summary"]["successful_tasks"] == 2
        
        # Generate playbook with default settings (exclude failed - but all are successful)
        playbook_result = await client.call_tool("generate_playbook", {
            "playbook_name": "success_only_playbook",
            "include_failed": False
        })
        
        # Should include all successful tasks
        assert playbook_result.data["status"] == "success"
        assert playbook_result.data["metadata"]["task_count"] == 2
        assert len(playbook_result.data["playbook"]["tasks"]) == 2
        
        # Generate playbook including failed tasks (same result since no failed tasks)
        playbook_result = await client.call_tool("generate_playbook", {
            "playbook_name": "all_tasks_playbook",
            "include_failed": True
        })
        
        # Should include all tasks
        assert playbook_result.data["status"] == "success"
        assert playbook_result.data["metadata"]["task_count"] == 2
        assert len(playbook_result.data["playbook"]["tasks"]) == 2


@pytest.mark.asyncio 
async def test_playbook_task_persistence():
    """Test that playbook tasks persist across different tool calls."""
    from src.ftl_mcp.server import mcp
    
    async with Client(mcp) as client:
        # Clear existing tasks
        await client.call_tool("clear_playbook_tasks", {})
        
        # Execute first task
        await client.call_tool("ansible_module", {
            "module_name": "argtest",
            "hosts": "localhost",
            "module_args": {"message": "first task"}
        })
        
        # Check task count
        tasks_result = await client.call_tool("get_playbook_tasks", {})
        assert tasks_result.data["summary"]["total_tasks"] == 1
        
        # Execute second task
        await client.call_tool("ansible_module", {
            "module_name": "timetest", 
            "hosts": "localhost",
            "module_args": {}
        })
        
        # Check that both tasks are recorded
        tasks_result = await client.call_tool("get_playbook_tasks", {})
        assert tasks_result.data["summary"]["total_tasks"] == 2
        
        # Verify both modules are present
        modules = tasks_result.data["summary"]["unique_modules"]
        assert "argtest" in modules
        assert "timetest" in modules