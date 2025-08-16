"""FTL MCP server implementation using fastmcp."""

from pathlib import Path

import yaml
from fastmcp import Context, FastMCP

from ftl_mcp.state import (
    InventoryData,
    InventoryGroup,
    InventoryHost,
    SessionActivity,
    SessionData,
    state_manager,
)
from ftl_mcp.tools import get_current_time as _get_current_time
from ftl_mcp.tools import list_environment_variables as _list_environment_variables
from ftl_mcp.tools import read_file as _read_file
from ftl_mcp.ftl_integration import (
    execute_ansible_module,
    execute_setup_module,
    execute_command_module,
    close_ftl_connections,
    FTLExecutionError,
    task_logger,
)
from ftl_mcp.secrets import secrets_manager

# Create the MCP server
mcp = FastMCP("ftl-mcp")

# In-memory storage for inventory (since StateManager is used for sessions/missions)
_inventory_storage = {"ansible_inventory": None, "inventory_history": []}




@mcp.tool()
async def get_context_info(ctx: Context) -> dict:
    """Get information about the current MCP context.

    Returns:
        Dictionary with context information
    """
    await ctx.info("Client requested context information")

    context_info = {
        "request_id": ctx.request_id,
        "client_id": ctx.client_id or "Unknown",
        "server_name": "ftl-mcp",
        "context_available": True,
        "timestamp": _get_current_time(),
    }

    await ctx.debug(f"Context info: {context_info}")
    return context_info








@mcp.tool()
async def start_session_tracker(session_name: str, ctx: Context) -> dict:
    """Start a new session tracker using the FastMCP session ID.

    Args:
        session_name: Human-readable name for this session

    Returns:
        Dictionary with session information
    """
    session_id = getattr(ctx, "session_id", None) or f"session_{ctx.request_id}"
    await ctx.info(
        f"Client {ctx.client_id or 'Unknown'} starting session tracker: {session_name}"
    )

    # Initialize session data using Pydantic model
    current_time = _get_current_time()
    session_data = SessionData(
        session_id=session_id,
        session_name=session_name,
        start_time=current_time,
        client_id=ctx.client_id or "Unknown",
        request_count=1,
        last_activity=current_time,
        activities=[
            SessionActivity(
                timestamp=current_time,
                action="session_started",
                request_id=ctx.request_id,
            )
        ],
        session_data={},
    )

    # Store in state manager
    state_manager.set_session(session_id, session_data)

    await ctx.info(
        f"Session tracker '{session_name}' initialized with ID: {session_id}"
    )

    return {
        "status": "started",
        "session_id": session_id,
        "session_name": session_name,
        "start_time": session_data.start_time,
        "client_id": session_data.client_id,
    }


@mcp.tool()
async def update_session_data(key: str, value: str, ctx: Context) -> dict:
    """Update session-specific data using the session ID.

    Args:
        key: Key to store the data under
        value: Value to store

    Returns:
        Dictionary with update status
    """
    session_id = getattr(ctx, "session_id", None) or f"session_{ctx.request_id}"
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} updating session data: {key}")

    # Get or create session data
    session_data = state_manager.get_session(session_id)
    if not session_data:
        await ctx.warning(
            f"No session found for ID: {session_id}, creating new session"
        )
        current_time = _get_current_time()
        session_data = SessionData(
            session_id=session_id,
            session_name="Auto-created",
            start_time=current_time,
            client_id=ctx.client_id or "Unknown",
            request_count=0,
            last_activity=current_time,
            activities=[],
            session_data={},
        )

    # Update session activity
    current_time = _get_current_time()
    session_data.request_count += 1
    session_data.last_activity = current_time
    session_data.activities.append(
        SessionActivity(
            timestamp=current_time,
            action="data_update",
            request_id=ctx.request_id,
            details=f"Updated key '{key}'",
        )
    )

    # Store the data
    old_value = session_data.session_data.get(key)
    session_data.session_data[key] = value

    # Save back to state manager
    state_manager.set_session(session_id, session_data)

    await ctx.debug(f"Updated session data: {key} = {value}")

    return {
        "status": "updated",
        "session_id": session_id,
        "key": key,
        "old_value": old_value,
        "new_value": value,
        "request_count": session_data.request_count,
        "last_activity": session_data.last_activity,
    }


@mcp.tool()
async def get_session_info(ctx: Context) -> dict:
    """Get information about the current session using session ID.

    Returns:
        Dictionary with comprehensive session information
    """
    session_id = getattr(ctx, "session_id", None) or f"session_{ctx.request_id}"
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} requesting session info")

    session_data = state_manager.get_session(session_id)
    if not session_data:
        await ctx.debug(f"No session data found for ID: {session_id}")
        active_sessions = list(state_manager.list_sessions().keys())
        return {
            "session_found": False,
            "session_id": session_id,
            "message": "No session tracker started. Use start_session_tracker first.",
            "active_sessions": active_sessions,
        }

    # Update activity
    current_time = _get_current_time()
    session_data.request_count += 1
    session_data.last_activity = current_time
    session_data.activities.append(
        SessionActivity(
            timestamp=current_time,
            action="info_request",
            request_id=ctx.request_id,
        )
    )

    # Save back to state manager
    state_manager.set_session(session_id, session_data)

    await ctx.debug(f"Retrieved session info for: {session_data.session_name}")

    return {
        "session_found": True,
        "session_id": session_id,
        "session_name": session_data.session_name,
        "start_time": session_data.start_time,
        "client_id": session_data.client_id,
        "request_count": session_data.request_count,
        "last_activity": session_data.last_activity,
        "session_data_keys": list(session_data.session_data.keys()),
        "session_data": session_data.session_data,
        "recent_activities": [
            activity.model_dump() for activity in session_data.activities[-5:]
        ],  # Last 5 activities
        "total_activities": len(session_data.activities),
    }


@mcp.tool()
async def list_active_sessions(ctx: Context) -> dict:
    """List all active sessions being tracked.

    Returns:
        Dictionary with information about all active sessions
    """
    await ctx.info(
        f"Client {ctx.client_id or 'Unknown'} requesting active sessions list"
    )

    sessions = state_manager.list_sessions()
    if not sessions:
        await ctx.debug("No active sessions found")
        return {
            "active_session_count": 0,
            "sessions": [],
            "message": "No active sessions",
        }

    # Build session summary
    sessions_summary = []
    for session_id, session_data in sessions.items():
        summary = {
            "session_id": session_id,
            "session_name": session_data.session_name,
            "start_time": session_data.start_time,
            "client_id": session_data.client_id,
            "request_count": session_data.request_count,
            "last_activity": session_data.last_activity,
            "data_keys": list(session_data.session_data.keys()),
            "data_count": len(session_data.session_data),
        }
        sessions_summary.append(summary)

    await ctx.debug(f"Found {len(sessions_summary)} active sessions")

    return {
        "active_session_count": len(sessions_summary),
        "sessions": sessions_summary,
        "current_session_id": getattr(ctx, "session_id", None)
        or f"session_{ctx.request_id}",
    }


@mcp.tool()
async def clear_session_data(ctx: Context) -> dict:
    """Clear data for the current session.

    Returns:
        Dictionary with clear operation status
    """
    session_id = getattr(ctx, "session_id", None) or f"session_{ctx.request_id}"
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} clearing session data")

    session_data = state_manager.get_session(session_id)
    if not session_data:
        await ctx.warning(f"No session found for ID: {session_id}")
        return {
            "status": "not_found",
            "session_id": session_id,
            "message": "No session data to clear",
        }

    data_keys_cleared = list(session_data.session_data.keys())
    data_count_cleared = len(session_data.session_data)

    # Clear session data but keep session metadata
    current_time = _get_current_time()
    session_data.session_data = {}
    session_data.request_count += 1
    session_data.last_activity = current_time
    session_data.activities.append(
        SessionActivity(
            timestamp=current_time,
            action="data_cleared",
            request_id=ctx.request_id,
            details=f"Cleared {data_count_cleared} data items",
        )
    )

    # Save back to state manager
    state_manager.set_session(session_id, session_data)

    await ctx.info(
        f"Cleared {data_count_cleared} items from session '{session_data.session_name}'"
    )

    return {
        "status": "cleared",
        "session_id": session_id,
        "session_name": session_data.session_name,
        "data_keys_cleared": data_keys_cleared,
        "items_cleared": data_count_cleared,
        "request_count": session_data.request_count,
    }




@mcp.tool()
async def load_inventory(inventory_path: str, ctx: Context) -> dict:
    """Load an Ansible YAML inventory file into context state management.

    Args:
        inventory_path: Path to the Ansible inventory YAML file

    Returns:
        Dictionary with inventory loading status and summary
    """
    await ctx.info(
        f"Client {ctx.client_id or 'Unknown'} loading inventory: {inventory_path}"
    )

    try:
        # Read and parse the inventory file
        inventory_file = Path(inventory_path)
        if not inventory_file.exists():
            await ctx.error(f"Inventory file does not exist: {inventory_path}")
            return {"error": f"Inventory file does not exist: {inventory_path}"}

        if not inventory_file.is_file():
            await ctx.error(f"Inventory path is not a file: {inventory_path}")
            return {"error": f"Inventory path is not a file: {inventory_path}"}

        # Load YAML content
        with open(inventory_file, "r", encoding="utf-8") as f:
            inventory_data = yaml.safe_load(f)

        if not inventory_data:
            await ctx.warning("Inventory file appears to be empty")
            return {"error": "Inventory file appears to be empty"}

        # Parse and validate Ansible inventory structure
        parsed_inventory = {
            "source_file": str(inventory_file.absolute()),
            "loaded_at": _get_current_time(),
            "groups": {},
            "hosts": {},
            "vars": {},
            "total_hosts": 0,
            "total_groups": 0,
        }

        # Helper function to process group data
        def process_group(group_name, group_data):
            group_info = {"hosts": [], "vars": {}, "children": []}

            if "hosts" in group_data:
                for host_name, host_data in group_data["hosts"].items():
                    host_info = {
                        "name": host_name,
                        "vars": host_data if isinstance(host_data, dict) else {},
                        "groups": [group_name],
                    }
                    # Add to or update existing host info
                    if host_name in parsed_inventory["hosts"]:
                        parsed_inventory["hosts"][host_name]["groups"].append(
                            group_name
                        )
                    else:
                        parsed_inventory["hosts"][host_name] = host_info
                    group_info["hosts"].append(host_name)

            if "vars" in group_data:
                group_info["vars"] = group_data["vars"]

            if "children" in group_data:
                if isinstance(group_data["children"], dict):
                    group_info["children"] = list(group_data["children"].keys())
                else:
                    group_info["children"] = (
                        group_data["children"]
                        if isinstance(group_data["children"], list)
                        else []
                    )

            parsed_inventory["groups"][group_name] = group_info

        # Process inventory structure
        for key, value in inventory_data.items():
            if key == "all":
                # Handle 'all' group specially
                if isinstance(value, dict):
                    if "vars" in value:
                        parsed_inventory["vars"].update(value["vars"])
                    if "children" in value:
                        # Process children defined under 'all'
                        if isinstance(value["children"], dict):
                            # Children are defined inline under 'all'
                            for child_name, child_data in value["children"].items():
                                process_group(child_name, child_data)
                        else:
                            # Children are references to top-level groups
                            for child_name in value["children"]:
                                if child_name in inventory_data:
                                    process_group(
                                        child_name, inventory_data[child_name]
                                    )
                    # Also process 'all' as a regular group to handle direct hosts
                    process_group("all", value)
            elif isinstance(value, dict) and key not in parsed_inventory["groups"]:
                # Process top-level groups that weren't already processed as children of 'all'
                process_group(key, value)

        # Calculate totals
        parsed_inventory["total_hosts"] = len(parsed_inventory["hosts"])
        parsed_inventory["total_groups"] = len(parsed_inventory["groups"])

        # Store in in-memory storage
        _inventory_storage["ansible_inventory"] = parsed_inventory
        _inventory_storage["inventory_history"] = [inventory_path]

        await ctx.info(
            f"Successfully loaded inventory with {parsed_inventory['total_hosts']} hosts and {parsed_inventory['total_groups']} groups"
        )

        return {
            "status": "success",
            "inventory_file": inventory_path,
            "total_hosts": parsed_inventory["total_hosts"],
            "total_groups": parsed_inventory["total_groups"],
            "groups": list(parsed_inventory["groups"].keys()),
            "hosts": list(parsed_inventory["hosts"].keys()),
            "loaded_at": parsed_inventory["loaded_at"],
        }

    except yaml.YAMLError as e:
        error_msg = f"YAML parsing error: {str(e)}"
        await ctx.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Error loading inventory: {str(e)}"
        await ctx.error(error_msg)
        return {"error": error_msg}


@mcp.tool()
async def get_inventory_status(ctx: Context) -> dict:
    """Get the current Ansible inventory status from context state.

    Returns:
        Dictionary with inventory information
    """
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} requesting inventory status")

    # Debug: Log context info
    await ctx.debug(f"Context request_id: {ctx.request_id}, client_id: {ctx.client_id}")

    # Get inventory from in-memory storage
    inventory = _inventory_storage["ansible_inventory"]
    history = _inventory_storage["inventory_history"]

    # Debug: Log what we found in state
    await ctx.debug(f"Found inventory in state: {inventory is not None}")
    if inventory:
        await ctx.debug(f"Inventory has {len(inventory.get('hosts', {}))} hosts")

    if not inventory:
        await ctx.debug("No inventory loaded in memory storage")
        return {
            "inventory_loaded": False,
            "message": "No inventory loaded",
            "history": history,
        }

    await ctx.debug(f"Retrieved inventory with {inventory['total_hosts']} hosts")

    return {
        "inventory_loaded": True,
        "source_file": inventory["source_file"],
        "loaded_at": inventory["loaded_at"],
        "total_hosts": inventory["total_hosts"],
        "total_groups": inventory["total_groups"],
        "groups": list(inventory["groups"].keys()),
        "hosts": list(inventory["hosts"].keys()),
        "history": history,
    }


@mcp.tool()
async def get_inventory_hosts(group_name: str = None, ctx: Context = None) -> dict:
    """Get hosts from the loaded Ansible inventory, optionally filtered by group.

    Args:
        group_name: Optional group name to filter hosts (if not provided, returns all hosts)

    Returns:
        Dictionary with host information
    """
    if not ctx:
        return {"error": "Context not available"}

    await ctx.info(
        f"Client {ctx.client_id or 'Unknown'} requesting hosts"
        + (f" in group '{group_name}'" if group_name else "")
    )

    # Get inventory from fallback storage
    inventory = _inventory_storage["ansible_inventory"]

    if not inventory:
        await ctx.warning("No inventory loaded in memory storage")
        return {
            "error": "No inventory loaded. Load an inventory first using load_inventory."
        }

    if group_name:
        # Filter by group
        if group_name not in inventory["groups"]:
            await ctx.warning(f"Group '{group_name}' not found in inventory")
            return {"error": f"Group '{group_name}' not found in inventory"}

        group_hosts = inventory["groups"][group_name]["hosts"]
        filtered_hosts = {
            host: inventory["hosts"][host]
            for host in group_hosts
            if host in inventory["hosts"]
        }

        await ctx.debug(
            f"Retrieved {len(filtered_hosts)} hosts from group '{group_name}'"
        )
        return {
            "group": group_name,
            "host_count": len(filtered_hosts),
            "hosts": filtered_hosts,
        }
    else:
        # Return all hosts
        await ctx.debug(f"Retrieved all {len(inventory['hosts'])} hosts")
        return {
            "group": "all",
            "host_count": len(inventory["hosts"]),
            "hosts": inventory["hosts"],
        }


@mcp.tool()
async def get_inventory_groups(ctx: Context) -> dict:
    """Get all groups from the loaded Ansible inventory.

    Returns:
        Dictionary with group information
    """
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} requesting inventory groups")

    # Get inventory from fallback storage
    inventory = _inventory_storage["ansible_inventory"]

    if not inventory:
        await ctx.warning("No inventory loaded in memory storage")
        return {
            "error": "No inventory loaded. Load an inventory first using load_inventory."
        }

    await ctx.debug(f"Retrieved {len(inventory['groups'])} groups")

    return {"group_count": len(inventory["groups"]), "groups": inventory["groups"]}


@mcp.tool()
async def save_inventory(output_path: str, ctx: Context) -> dict:
    """Save the current Ansible inventory from context state to a YAML file.

    Args:
        output_path: Path where the inventory YAML file should be saved

    Returns:
        Dictionary with save operation status and details
    """
    await ctx.info(
        f"Client {ctx.client_id or 'Unknown'} saving inventory to: {output_path}"
    )

    # Retrieve inventory from fallback storage
    inventory = _inventory_storage["ansible_inventory"]

    if not inventory:
        await ctx.warning("No inventory found in memory storage")
        return {
            "error": "No inventory loaded. Load an inventory first using load_inventory."
        }

    try:
        output_file = Path(output_path)

        # Create parent directories if they don't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Reconstruct Ansible inventory structure from parsed data
        ansible_inventory = {}

        # Add global vars from inventory (these go under 'all')
        if inventory.get("vars"):
            ansible_inventory["all"] = {"vars": inventory["vars"]}

        # Process groups
        for group_name, group_info in inventory["groups"].items():
            group_data = {}

            # Add hosts to group
            if group_info.get("hosts"):
                group_data["hosts"] = {}
                for host_name in group_info["hosts"]:
                    if host_name in inventory["hosts"]:
                        host_vars = inventory["hosts"][host_name].get("vars", {})
                        if host_vars:
                            group_data["hosts"][host_name] = host_vars
                        else:
                            group_data["hosts"][host_name] = {}

            # Add group vars
            if group_info.get("vars"):
                group_data["vars"] = group_info["vars"]

            # Add children
            if group_info.get("children"):
                group_data["children"] = {}
                for child in group_info["children"]:
                    group_data["children"][child] = {}

            ansible_inventory[group_name] = group_data

        # Write YAML file
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(
                ansible_inventory,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        await ctx.info(f"Successfully saved inventory to {output_path}")

        return {
            "status": "success",
            "output_file": str(output_file.absolute()),
            "total_hosts": inventory["total_hosts"],
            "total_groups": inventory["total_groups"],
            "groups": list(inventory["groups"].keys()),
            "saved_at": _get_current_time(),
        }

    except PermissionError as e:
        error_msg = f"Permission denied writing to {output_path}: {str(e)}"
        await ctx.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Error saving inventory: {str(e)}"
        await ctx.error(error_msg)
        return {"error": error_msg}


@mcp.resource("file://{path}")
async def read_file(path: str, ctx: Context) -> str:
    """Read the contents of a file.

    Args:
        path: Path to the file to read

    Returns:
        File contents as string
    """
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} reading file: {path}")

    try:
        result = _read_file(path)
        if result.startswith("Error:"):
            await ctx.warning(f"File read failed: {result}")
        else:
            file_size = len(result)
            await ctx.debug(f"Successfully read file ({file_size} characters)")
        return result
    except Exception as e:
        await ctx.error(f"File read error: {str(e)}")
        raise


@mcp.resource("env://")
async def list_environment_variables(ctx: Context) -> dict:
    """List all environment variables."""
    await ctx.info(
        f"Client {ctx.client_id or 'Unknown'} requested environment variables"
    )

    try:
        result = _list_environment_variables()
        await ctx.debug(f"Returned {len(result)} environment variables")
        return result
    except Exception as e:
        await ctx.error(f"Environment variables error: {str(e)}")
        raise


# =============================================================================
# Ansible Module Execution Tools (using faster_than_light)
# =============================================================================

@mcp.tool()
async def ansible_module(
    module_name: str,
    hosts: str,
    module_args: dict = None,
    ctx: Context = None
) -> dict:
    """Execute any Ansible module using faster_than_light.
    
    Args:
        module_name: Name of the Ansible module to execute (e.g., "setup", "command", "copy")
        hosts: Comma-separated list of target hosts or single hostname
        module_args: Dictionary of arguments to pass to the module
        
    Returns:
        Dictionary with execution results for each host
    """
    if not ctx:
        return {"error": "Context not available"}
        
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} executing Ansible module: {module_name}")
    
    try:
        # Parse hosts string into list
        host_list = [host.strip() for host in hosts.split(",") if host.strip()]
        
        if not host_list:
            await ctx.error("No valid hosts specified")
            return {"error": "No valid hosts specified"}
            
        # Execute module via FTL integration
        result = await execute_ansible_module(
            module_name=module_name,
            hosts=host_list,
            module_args=module_args or {},
            ctx=ctx
        )
        
        # Store execution in state manager
        execution_record = {
            "module": module_name,
            "hosts": host_list,
            "args": module_args or {},
            "timestamp": _get_current_time(),
            "summary": result.get("execution_summary", {}),
            "success": result.get("status") == "success"
        }
        state_manager.set_generic(f"ansible_execution_{_get_current_time()}", execution_record)
        
        await ctx.info(f"Ansible module '{module_name}' execution completed")
        return result
        
    except FTLExecutionError as e:
        await ctx.error(f"FTL execution failed: {str(e)}")
        return {"error": f"Module execution failed: {str(e)}"}
    except Exception as e:
        await ctx.error(f"Unexpected error executing module: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}


@mcp.tool()
async def ansible_setup(hosts: str, ctx: Context = None) -> dict:
    """Gather facts from hosts using the Ansible setup module.
    
    Args:
        hosts: Comma-separated list of target hosts or single hostname
        
    Returns:
        Dictionary with gathered facts for each host
    """
    if not ctx:
        return {"error": "Context not available"}
        
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} gathering facts from hosts: {hosts}")
    
    try:
        # Parse hosts string into list
        host_list = [host.strip() for host in hosts.split(",") if host.strip()]
        
        # Execute setup module
        result = await execute_setup_module(hosts=host_list, ctx=ctx)
        
        # Store facts in state manager for later use
        if result.get("status") == "success":
            facts_record = {
                "operation": "gather_facts",
                "hosts": host_list,
                "timestamp": _get_current_time(),
                "facts_summary": {
                    host: {
                        "os_family": facts.get("ansible_facts", {}).get("ansible_os_family"),
                        "distribution": facts.get("ansible_facts", {}).get("ansible_distribution"),
                        "python_version": facts.get("ansible_facts", {}).get("ansible_python_version")
                    }
                    for host, facts in result.get("results", {}).items()
                    if "ansible_facts" in facts
                }
            }
            state_manager.set_generic(f"facts_{_get_current_time()}", facts_record)
        
        await ctx.info(f"Facts gathering completed for {len(host_list)} hosts")
        return result
        
    except Exception as e:
        await ctx.error(f"Error gathering facts: {str(e)}")
        return {"error": f"Facts gathering failed: {str(e)}"}


@mcp.tool()
async def ansible_command(command: str, hosts: str, ctx: Context = None) -> dict:
    """Execute a shell command on hosts using the Ansible command module.
    
    Args:
        command: Shell command to execute
        hosts: Comma-separated list of target hosts or single hostname
        
    Returns:
        Dictionary with command execution results for each host
    """
    if not ctx:
        return {"error": "Context not available"}
        
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} executing command on hosts: {hosts}")
    await ctx.debug(f"Command: {command}")
    
    try:
        # Parse hosts string into list
        host_list = [host.strip() for host in hosts.split(",") if host.strip()]
        
        # Execute command module
        result = await execute_command_module(command=command, hosts=host_list, ctx=ctx)
        
        # Store command execution record
        command_record = {
            "operation": "command_execution",
            "command": command,
            "hosts": host_list,
            "timestamp": _get_current_time(),
            "summary": result.get("execution_summary", {}),
            "success": result.get("status") == "success"
        }
        state_manager.set_generic(f"command_{_get_current_time()}", command_record)
        
        await ctx.info(f"Command execution completed on {len(host_list)} hosts")
        return result
        
    except Exception as e:
        await ctx.error(f"Error executing command: {str(e)}")
        return {"error": f"Command execution failed: {str(e)}"}


@mcp.tool()
async def ansible_copy(
    src: str,
    dest: str, 
    hosts: str,
    backup: bool = False,
    mode: str = None,
    ctx: Context = None
) -> dict:
    """Copy files to hosts using the Ansible copy module.
    
    Args:
        src: Source file path on the control machine
        dest: Destination path on target hosts  
        hosts: Comma-separated list of target hosts or single hostname
        backup: Create backup of destination file if it exists
        mode: File permissions for the destination file
        
    Returns:
        Dictionary with copy operation results for each host
    """
    if not ctx:
        return {"error": "Context not available"}
        
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} copying file to hosts: {hosts}")
    await ctx.debug(f"Copy: {src} -> {dest}")
    
    try:
        # Parse hosts string into list
        host_list = [host.strip() for host in hosts.split(",") if host.strip()]
        
        # Prepare copy module arguments
        copy_args = {
            "src": src,
            "dest": dest
        }
        if backup:
            copy_args["backup"] = "yes"
        if mode:
            copy_args["mode"] = mode
            
        # Execute copy module
        result = await execute_ansible_module(
            module_name="copy",
            hosts=host_list,
            module_args=copy_args,
            ctx=ctx
        )
        
        # Store copy operation record
        copy_record = {
            "operation": "file_copy", 
            "src": src,
            "dest": dest,
            "hosts": host_list,
            "timestamp": _get_current_time(),
            "summary": result.get("execution_summary", {}),
            "success": result.get("status") == "success"
        }
        state_manager.set_generic(f"copy_{_get_current_time()}", copy_record)
        
        await ctx.info(f"File copy completed to {len(host_list)} hosts")
        return result
        
    except Exception as e:
        await ctx.error(f"Error copying file: {str(e)}")
        return {"error": f"File copy failed: {str(e)}"}


@mcp.tool()
async def close_ansible_connections(ctx: Context = None) -> dict:
    """Close all faster_than_light connections and clean up resources.
    
    Returns:
        Dictionary with cleanup status
    """
    if not ctx:
        return {"error": "Context not available"}
        
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} closing FTL connections")
    
    try:
        await close_ftl_connections(ctx)
        await ctx.info("FTL connections closed successfully")
        return {"status": "success", "message": "All FTL connections closed"}
        
    except Exception as e:
        await ctx.error(f"Error closing FTL connections: {str(e)}")
        return {"error": f"Failed to close connections: {str(e)}"}


# =============================================================================
# Playbook Generation Tools
# =============================================================================

@mcp.tool()
async def get_playbook_tasks(ctx: Context = None) -> dict:
    """Get recorded tasks that can be converted to an Ansible playbook.
    
    Returns:
        Dictionary with recorded tasks and metadata
    """
    if not ctx:
        return {"error": "Context not available"}
        
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} requesting playbook tasks")
    
    try:
        tasks = task_logger.get_tasks()
        
        # Calculate summary statistics
        total_tasks = len(tasks)
        successful_tasks = sum(1 for t in tasks if t.get("success", False))
        changed_tasks = sum(1 for t in tasks if t.get("changed", False))
        unique_hosts = set()
        unique_modules = set()
        
        for task in tasks:
            unique_hosts.update(task.get("hosts", []))
            unique_modules.add(task.get("module", ""))
        
        await ctx.info(f"Retrieved {total_tasks} recorded tasks")
        
        return {
            "tasks": tasks,
            "summary": {
                "total_tasks": total_tasks,
                "successful_tasks": successful_tasks,
                "failed_tasks": total_tasks - successful_tasks,
                "changed_tasks": changed_tasks,
                "unique_hosts": list(unique_hosts),
                "unique_modules": list(unique_modules),
                "host_count": len(unique_hosts),
                "module_count": len(unique_modules)
            }
        }
        
    except Exception as e:
        await ctx.error(f"Error retrieving playbook tasks: {str(e)}")
        return {"error": f"Failed to retrieve tasks: {str(e)}"}


@mcp.tool()
async def generate_playbook(
    playbook_name: str = "generated_playbook",
    include_failed: bool = False,
    ctx: Context = None
) -> dict:
    """Generate an Ansible playbook from recorded tasks.
    
    Args:
        playbook_name: Name for the generated playbook
        include_failed: Whether to include tasks that failed during execution
        
    Returns:
        Dictionary with generated playbook data and YAML
    """
    if not ctx:
        return {"error": "Context not available"}
        
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} generating playbook: {playbook_name}")
    
    try:
        tasks = task_logger.get_tasks()
        
        # Filter tasks based on success
        if not include_failed:
            original_count = len(tasks)
            tasks = [t for t in tasks if t.get("success", False)]
            filtered_count = len(tasks)
            if original_count > filtered_count:
                await ctx.info(f"Filtered out {original_count - filtered_count} failed tasks")
        
        if not tasks:
            await ctx.warning("No tasks available for playbook generation")
            return {"error": "No tasks recorded or all tasks failed"}
        
        # Determine if we need to gather facts
        gather_facts = any(t["module"] == "setup" for t in tasks)
        
        # Get all unique hosts from tasks
        all_hosts = set()
        for task in tasks:
            all_hosts.update(task.get("hosts", []))
        
        # Generate playbook structure
        playbook = {
            "name": playbook_name,
            "hosts": "{{ target_hosts | default('all') }}",
            "gather_facts": gather_facts,
            "tasks": []
        }
        
        # Convert tasks to playbook format
        for task in tasks:
            playbook_task = {
                "name": task["name"]
            }
            
            # Add the module and its arguments
            module_name = task["module"]
            module_args = task["args"]
            
            if module_args:
                playbook_task[module_name] = module_args
            else:
                playbook_task[module_name] = {}
            
            playbook["tasks"].append(playbook_task)
        
        # Generate YAML representation
        playbook_yaml = yaml.dump([playbook], default_flow_style=False, sort_keys=False)
        
        await ctx.info(f"Generated playbook with {len(tasks)} tasks targeting {len(all_hosts)} hosts")
        
        return {
            "status": "success",
            "playbook_name": playbook_name,
            "playbook": playbook,
            "yaml": playbook_yaml,
            "metadata": {
                "task_count": len(tasks),
                "host_count": len(all_hosts),
                "hosts": list(all_hosts),
                "modules_used": list(set(t["module"] for t in tasks)),
                "gather_facts": gather_facts,
                "generated_at": _get_current_time()
            }
        }
        
    except Exception as e:
        await ctx.error(f"Error generating playbook: {str(e)}")
        return {"error": f"Failed to generate playbook: {str(e)}"}


@mcp.tool()
async def clear_playbook_tasks(ctx: Context = None) -> dict:
    """Clear the recorded task history.
    
    Returns:
        Dictionary with clear operation status
    """
    if not ctx:
        return {"error": "Context not available"}
        
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} clearing playbook task history")
    
    try:
        tasks_before = len(task_logger.get_tasks())
        task_logger.clear_tasks()
        
        await ctx.info(f"Cleared {tasks_before} recorded tasks")
        
        return {
            "status": "success",
            "message": f"Cleared {tasks_before} recorded tasks",
            "tasks_cleared": tasks_before,
            "cleared_at": _get_current_time()
        }
        
    except Exception as e:
        await ctx.error(f"Error clearing playbook tasks: {str(e)}")
        return {"error": f"Failed to clear tasks: {str(e)}"}


# =============================================================================
# Secrets Management Tools (Secure - No Exposure to MCP Clients)
# =============================================================================

@mcp.tool()
async def get_secrets_status(ctx: Context = None) -> dict:
    """Get status of the secrets manager (safe information only).
    
    This tool provides information about loaded secrets without exposing
    any secret values. Safe for use by MCP clients like Claude Code.
    
    Returns:
        Dictionary with secrets manager status and statistics
    """
    if not ctx:
        return {"error": "Context not available"}
        
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} requesting secrets status")
    
    try:
        stats = secrets_manager.get_stats()
        secret_names = secrets_manager.list_secret_names()
        
        # Get metadata for each secret (safe to expose)
        secrets_info = []
        for name in secret_names:
            metadata = secrets_manager.get_secret_metadata(name)
            if metadata:
                secrets_info.append({
                    "name": metadata.name,
                    "description": metadata.description,
                    "created_at": metadata.created_at,
                    "updated_at": metadata.updated_at,
                    "tags": metadata.tags
                })
        
        await ctx.info(f"Retrieved status for {stats['total_secrets']} secrets")
        
        return {
            "status": "success",
            "statistics": stats,
            "secrets": secrets_info,
            "loading_instructions": {
                "environment_variables": "Set FTL_SECRET_<NAME>=<value> environment variables",
                "encrypted_file": "Manual file creation with SecretsManager.save_to_encrypted_file()",
                "encryption_key": "Set FTL_MCP_ENCRYPTION_KEY environment variable"
            }
        }
        
    except Exception as e:
        await ctx.error(f"Error getting secrets status: {str(e)}")
        return {"error": f"Failed to get secrets status: {str(e)}"}



@mcp.tool()
async def check_secret_exists(name: str, ctx: Context = None) -> dict:
    """Check if a secret exists (safe - no secret values exposed).
    
    Args:
        name: Secret name to check
        
    Returns:
        Dictionary with existence status and metadata
    """
    if not ctx:
        return {"error": "Context not available"}
        
    await ctx.debug(f"Client {ctx.client_id or 'Unknown'} checking if secret exists: {name}")
    
    try:
        exists = secrets_manager.has_secret(name)
        
        result = {
            "secret_name": name,
            "exists": exists
        }
        
        if exists:
            metadata = secrets_manager.get_secret_metadata(name)
            if metadata:
                result["metadata"] = {
                    "description": metadata.description,
                    "created_at": metadata.created_at,
                    "updated_at": metadata.updated_at,
                    "tags": metadata.tags
                }
        
        await ctx.debug(f"Secret '{name}' exists: {exists}")
        return result
        
    except Exception as e:
        await ctx.error(f"Error checking secret existence: {str(e)}")
        return {"error": f"Failed to check secret: {str(e)}"}


@mcp.tool()
async def reload_secrets(ctx: Context = None) -> dict:
    """Reload secrets from environment variables and encrypted files.
    
    This tool clears all existing secrets and reloads them fresh from external 
    sources (environment variables and encrypted files) without exposing secret values.
    
    Returns:
        Dictionary with reload results and statistics
    """
    if not ctx:
        return {"error": "Context not available"}
        
    await ctx.debug(f"Client {ctx.client_id or 'Unknown'} requesting secrets reload")
    
    try:
        result = secrets_manager.reload_secrets()
        
        await ctx.info(f"Secrets reloaded successfully: "
                       f"{result['final_count']} total secrets loaded")
        
        return {
            "status": "success",
            "reload_summary": {
                "initial_secret_count": result["initial_count"],
                "final_secret_count": result["final_count"],
                "reloaded_from_environment": result["reloaded_environment"],
                "reloaded_from_encrypted_file": result["reloaded_encrypted_file"]
            },
            "message": f"Successfully reloaded {result['final_count']} secrets from external sources."
        }
        
    except Exception as e:
        await ctx.error(f"Error reloading secrets: {str(e)}")
        return {"error": f"Failed to reload secrets: {str(e)}"}


def main():
    """Run the FTL MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
