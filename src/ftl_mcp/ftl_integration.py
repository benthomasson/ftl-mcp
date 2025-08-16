"""Integration layer for faster_than_light execution engine.

This module provides the bridge between FTL MCP tools and the faster_than_light
execution engine, enabling high-performance Ansible module execution through
MCP interfaces.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
import faster_than_light as ftl
from fastmcp import Context

from .state import state_manager
from .tools import get_current_time as _get_current_time
from .secrets import get_secret


class FTLExecutionError(Exception):
    """Exception raised when FTL module execution fails."""
    pass


class TaskLogger:
    """Logs Ansible module executions for playbook generation."""
    
    def __init__(self):
        self.tasks = []
    
    def log_task(self, module_name: str, hosts: List[str], args: dict, result: dict):
        """Log an executed task for playbook generation.
        
        Args:
            module_name: Name of the Ansible module executed
            hosts: List of target hosts
            args: Module arguments used
            result: Execution result from faster_than_light
        """
        task = {
            "name": f"Execute {module_name}",
            "module": module_name,
            "hosts": hosts,
            "args": args,
            "timestamp": _get_current_time(),
            "success": result.get("status") == "success",
            "changed": any(r.get("changed", False) for r in result.get("results", {}).values()) if result.get("results") else False
        }
        self.tasks.append(task)
        
        # Store in state manager for persistence
        state_manager.set_generic("playbook_tasks", self.tasks)
    
    def get_tasks(self) -> List[dict]:
        """Get all logged tasks."""
        # Load from state manager in case it was updated elsewhere
        stored_tasks = state_manager.get_generic("playbook_tasks")
        if stored_tasks:
            self.tasks = stored_tasks
        return self.tasks
    
    def clear_tasks(self):
        """Clear all logged tasks."""
        self.tasks = []
        state_manager.set_generic("playbook_tasks", [])


# Global task logger instance
task_logger = TaskLogger()


def get_ftl_modules_path() -> str:
    """Get the path to the ftl_modules package directory.
    
    Returns:
        Absolute path to the ftl_modules directory containing the modules
        
    Raises:
        ImportError: If ftl_modules package is not installed
    """
    try:
        # Try to import ftl_modules and get its path
        import ftl_modules
        module_path = Path(ftl_modules.__file__).parent
        return str(module_path)
    except ImportError:
        raise ImportError(
            "ftl_modules package not found. Please install it with: pip install -e ../ftl-modules"
        )


class FTLExecutor:
    """Manages faster_than_light execution for MCP tools."""
    
    def __init__(self):
        self._gate_cache: Dict[str, Any] = {}
        
    async def execute_module(
        self,
        module_name: str,
        hosts: Union[str, List[str]],
        module_args: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Execute an Ansible module using faster_than_light.
        
        Args:
            module_name: Name of the Ansible module to execute
            hosts: Target host(s) - single hostname or list of hostnames
            module_args: Arguments to pass to the module
            ctx: MCP context for logging
            
        Returns:
            Dictionary containing execution results for each host
            
        Raises:
            FTLExecutionError: If module execution fails
        """
        if ctx:
            await ctx.info(f"Executing module '{module_name}' on hosts: {hosts}")
            
        # Normalize hosts to list
        if isinstance(hosts, str):
            hosts = [hosts]
            
        # Prepare module arguments
        args = module_args or {}
        
        try:
            # Create inventory for target hosts
            inventory = await self._create_inventory_for_hosts(hosts, ctx)
            
            # Execute module via faster_than_light
            # Use ftl_modules package directory
            try:
                ftl_modules_path = get_ftl_modules_path()
                module_dirs = [ftl_modules_path]
                if ctx:
                    await ctx.debug(f"Using ftl_modules at: {ftl_modules_path}")
            except ImportError as e:
                # Fallback to faster_than_light test modules if ftl_modules not available
                module_dirs = ["/Users/ai/git/faster-than-light/tests/modules"]
                if ctx:
                    await ctx.warning(f"ftl_modules not found ({str(e)}), using fallback test modules")
                    await ctx.debug(f"Using fallback modules at: {module_dirs[0]}")
            
            results = await ftl.run_module(
                inventory=inventory,
                module_dirs=module_dirs,
                module_name=module_name,
                gate_cache=self._gate_cache,
                module_args=args
            )
            
            if ctx:
                success_count = sum(1 for result in results.values() 
                                  if result.get("changed") is not None or result.get("failed") is False)
                await ctx.info(f"Module execution completed: {success_count}/{len(hosts)} hosts succeeded")
                
            return {
                "status": "success",
                "module": module_name,
                "hosts": hosts,
                "results": results,
                "execution_summary": self._create_execution_summary(results)
            }
            
        except Exception as e:
            error_msg = f"FTL module execution failed: {str(e)}"
            if ctx:
                await ctx.error(error_msg)
            raise FTLExecutionError(error_msg) from e
    
    async def _create_inventory_for_hosts(
        self, 
        hosts: List[str], 
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Create an FTL inventory for the specified hosts.
        
        This method tries to use the loaded inventory from MCP state first,
        falling back to creating a basic inventory for the specified hosts.
        """
        # Try to get existing inventory from MCP state
        from .server import _inventory_storage
        existing_inventory = _inventory_storage.get("ansible_inventory")
        
        if existing_inventory and self._hosts_in_inventory(hosts, existing_inventory):
            if ctx:
                await ctx.debug("Using existing inventory from MCP state")
            return self._convert_mcp_inventory_to_ftl(existing_inventory, hosts)
        
        # Create basic inventory for the hosts
        if ctx:
            await ctx.debug(f"Creating basic inventory for hosts: {hosts}")
        return self._create_basic_inventory(hosts)
    
    def _hosts_in_inventory(self, hosts: List[str], inventory: Dict[str, Any]) -> bool:
        """Check if all hosts exist in the inventory."""
        inventory_hosts = inventory.get("hosts", {})
        return all(host in inventory_hosts for host in hosts)
    
    def _convert_mcp_inventory_to_ftl(
        self, 
        mcp_inventory: Dict[str, Any], 
        target_hosts: List[str]
    ) -> Dict[str, Any]:
        """Convert MCP inventory format to FTL inventory format.
        
        FTL expects Ansible-style inventory structure.
        """
        ftl_inventory = {
            "all": {
                "hosts": {},
                "vars": mcp_inventory.get("vars", {})
            }
        }
        
        # Add target hosts with their variables
        for host_name in target_hosts:
            if host_name in mcp_inventory.get("hosts", {}):
                host_data = mcp_inventory["hosts"][host_name]
                ftl_inventory["all"]["hosts"][host_name] = host_data.get("vars", {})
            else:
                # Basic host entry if not in inventory
                ftl_inventory["all"]["hosts"][host_name] = {}
                
        return ftl_inventory
    
    def _create_basic_inventory(self, hosts: List[str]) -> Dict[str, Any]:
        """Create a basic FTL inventory for the specified hosts."""
        inventory = {
            "all": {
                "hosts": {},
                "vars": {
                    "ansible_ssh_common_args": "-o StrictHostKeyChecking=no"
                }
            }
        }
        
        # Add SSH credentials from secrets if available
        ssh_user = get_secret("ssh_user")
        ssh_password = get_secret("ssh_password")
        ssh_key_file = get_secret("ssh_key_file")
        
        if ssh_user:
            inventory["all"]["vars"]["ansible_user"] = ssh_user
        if ssh_password:
            inventory["all"]["vars"]["ansible_password"] = ssh_password
        if ssh_key_file:
            inventory["all"]["vars"]["ansible_ssh_private_key_file"] = ssh_key_file
        
        for host in hosts:
            if host == "localhost":
                inventory["all"]["hosts"][host] = {
                    "ansible_connection": "local",
                    "ansible_python_interpreter": "/usr/bin/python3"
                }
            else:
                inventory["all"]["hosts"][host] = {}
                
        return inventory
    
    def _create_execution_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of execution results."""
        total_hosts = len(results)
        successful = sum(1 for result in results.values() 
                        if not result.get("failed", False))
        failed = total_hosts - successful
        changed = sum(1 for result in results.values() 
                     if result.get("changed", False))
        
        return {
            "total_hosts": total_hosts,
            "successful": successful,
            "failed": failed,
            "changed": changed,
            "success_rate": f"{(successful/total_hosts)*100:.1f}%" if total_hosts > 0 else "0%"
        }
    
    async def close_connections(self, ctx: Optional[Context] = None):
        """Close all FTL connections and clean up resources."""
        try:
            await ftl.close_gate()
            self._gate_cache.clear()
            if ctx:
                await ctx.debug("FTL connections closed and cache cleared")
        except Exception as e:
            if ctx:
                await ctx.warning(f"Error closing FTL connections: {str(e)}")


# Global FTL executor instance
ftl_executor = FTLExecutor()


# Convenience functions for common operations
async def execute_ansible_module(
    module_name: str,
    hosts: Union[str, List[str]], 
    module_args: Optional[Dict[str, Any]] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Execute an Ansible module using FTL.
    
    This is the main entry point for executing Ansible modules from MCP tools.
    """
    result = await ftl_executor.execute_module(module_name, hosts, module_args, ctx)
    
    # Log the task for playbook generation
    host_list = hosts if isinstance(hosts, list) else [hosts]
    task_logger.log_task(module_name, host_list, module_args or {}, result)
    
    return result


async def execute_setup_module(
    hosts: Union[str, List[str]],
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Execute the setup module to gather facts."""
    return await execute_ansible_module("setup", hosts, {}, ctx)


async def execute_command_module(
    command: str,
    hosts: Union[str, List[str]],
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Execute a shell command on hosts."""
    return await execute_ansible_module("command", hosts, {"cmd": command}, ctx)


async def close_ftl_connections(ctx: Optional[Context] = None):
    """Close all FTL connections."""
    await ftl_executor.close_connections(ctx)