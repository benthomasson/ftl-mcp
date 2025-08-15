"""FTL MCP server implementation using fastmcp."""

from pathlib import Path

import yaml
from fastmcp import Context, FastMCP

from .tools import calculate_speed as _calculate_speed
from .tools import get_current_time as _get_current_time
from .tools import list_directory as _list_directory
from .tools import list_environment_variables as _list_environment_variables
from .tools import read_file as _read_file

# Create the MCP server
mcp = FastMCP("ftl-mcp")

# In-memory storage for inventory data (fallback if context state doesn't work)
_inventory_storage = {"ansible_inventory": None, "inventory_history": []}

# Session-specific storage for demonstration
_session_storage = {}


@mcp.tool()
async def get_current_time(ctx: Context) -> str:
    """Get the current time in ISO format."""
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} requested current time")
    result = _get_current_time()
    await ctx.debug(f"Returning time: {result}")
    return result


@mcp.tool()
async def calculate_speed(distance: float, time: float, ctx: Context) -> dict:
    """Calculate speed given distance and time.

    Args:
        distance: Distance in kilometers
        time: Time in hours

    Returns:
        Dictionary with speed calculations
    """
    await ctx.info(
        f"Client {ctx.client_id or 'Unknown'} calculating speed: {distance}km in {time}h"
    )

    try:
        result = _calculate_speed(distance, time)
        is_ftl = result.get("is_faster_than_light", False)
        if is_ftl:
            await ctx.warning(
                f"⚡ FASTER THAN LIGHT detected! Speed: {result['speed_ms']:,.0f} m/s"
            )
        else:
            await ctx.debug(f"Normal speed calculated: {result['speed_kmh']} km/h")
        return result
    except ValueError as e:
        await ctx.error(f"Speed calculation failed: {str(e)}")
        raise


@mcp.tool()
async def list_directory(path: str = ".", ctx: Context = None) -> dict:
    """List contents of a directory.

    Args:
        path: Directory path to list (defaults to current directory)

    Returns:
        Dictionary with directory information
    """
    if ctx:
        await ctx.info(f"Client {ctx.client_id or 'Unknown'} listing directory: {path}")

    try:
        result = _list_directory(path)
        if "error" in result:
            if ctx:
                await ctx.warning(f"Directory listing failed: {result['error']}")
        else:
            if ctx:
                await ctx.debug(f"Listed {result['item_count']} items in {path}")
        return result
    except Exception as e:
        if ctx:
            await ctx.error(f"Directory listing error: {str(e)}")
        raise


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
async def start_ftl_mission(mission_name: str, destination: str, ctx: Context) -> dict:
    """Start a faster-than-light mission and store it in context state.

    Args:
        mission_name: Name of the FTL mission
        destination: Destination system/planet

    Returns:
        Dictionary with mission details
    """
    await ctx.info(
        f"Client {ctx.client_id or 'Unknown'} starting FTL mission: {mission_name}"
    )

    # Initialize mission state
    mission_data = {
        "name": mission_name,
        "destination": destination,
        "status": "planning",
        "start_time": _get_current_time(),
        "fuel_level": 100.0,
        "crew_count": 5,
        "distance_traveled": 0.0,
        "alerts": [],
    }

    # Store in context state
    ctx.set_state("current_mission", mission_data)
    ctx.set_state("mission_history", [mission_name])

    await ctx.info(f"Mission '{mission_name}' initialized in context state")
    return mission_data


@mcp.tool()
async def update_ftl_mission(
    status: str = None,
    fuel_consumed: float = 0.0,
    distance: float = 0.0,
    alert: str = None,
    ctx: Context = None,
) -> dict:
    """Update the current FTL mission status using context state.

    Args:
        status: New mission status (optional)
        fuel_consumed: Amount of fuel consumed (default: 0.0)
        distance: Distance traveled in light-years (default: 0.0)
        alert: Alert message to add (optional)

    Returns:
        Dictionary with updated mission details
    """
    if not ctx:
        return {"error": "Context not available"}

    await ctx.info(f"Client {ctx.client_id or 'Unknown'} updating FTL mission")

    # Retrieve current mission from state
    current_mission = ctx.get_state("current_mission")
    if not current_mission:
        await ctx.warning("No active mission found in context state")
        return {
            "error": "No active mission. Start a mission first using start_ftl_mission."
        }

    # Update mission data
    if status:
        current_mission["status"] = status
        await ctx.info(f"Mission status updated to: {status}")

    if fuel_consumed > 0:
        current_mission["fuel_level"] = max(
            0.0, current_mission["fuel_level"] - fuel_consumed
        )
        await ctx.debug(
            f"Fuel consumed: {fuel_consumed}, remaining: {current_mission['fuel_level']}"
        )

    if distance > 0:
        current_mission["distance_traveled"] += distance
        await ctx.debug(
            f"Distance traveled: +{distance}, total: {current_mission['distance_traveled']}"
        )

    if alert:
        current_mission["alerts"].append(
            {"timestamp": _get_current_time(), "message": alert}
        )
        await ctx.warning(f"Mission alert: {alert}")

    # Check for critical conditions
    if current_mission["fuel_level"] < 20.0:
        fuel_alert = f"LOW FUEL WARNING: {current_mission['fuel_level']:.1f}% remaining"
        current_mission["alerts"].append(
            {"timestamp": _get_current_time(), "message": fuel_alert}
        )
        await ctx.warning(fuel_alert)

    # Update state
    ctx.set_state("current_mission", current_mission)

    return current_mission


@mcp.tool()
async def get_ftl_mission_status(ctx: Context) -> dict:
    """Get the current FTL mission status from context state.

    Returns:
        Dictionary with current mission status
    """
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} requesting mission status")

    # Retrieve mission from state
    current_mission = ctx.get_state("current_mission")
    mission_history = ctx.get_state("mission_history") or []

    if not current_mission:
        await ctx.debug("No active mission in context state")
        return {
            "active_mission": None,
            "mission_history": mission_history,
            "message": "No active mission",
        }

    await ctx.debug(f"Retrieved mission: {current_mission['name']}")

    return {
        "active_mission": current_mission,
        "mission_history": mission_history,
        "state_info": {
            "context_id": ctx.request_id,
            "client_id": ctx.client_id or "Unknown",
        },
    }


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

    # Initialize session data
    session_data = {
        "session_id": session_id,
        "session_name": session_name,
        "start_time": _get_current_time(),
        "client_id": ctx.client_id or "Unknown",
        "request_count": 1,
        "last_activity": _get_current_time(),
        "activities": [
            {
                "timestamp": _get_current_time(),
                "action": "session_started",
                "request_id": ctx.request_id,
            }
        ],
        "session_data": {},
    }

    # Store in session storage
    _session_storage[session_id] = session_data

    await ctx.info(
        f"Session tracker '{session_name}' initialized with ID: {session_id}"
    )

    return {
        "status": "started",
        "session_id": session_id,
        "session_name": session_name,
        "start_time": session_data["start_time"],
        "client_id": session_data["client_id"],
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
    if session_id not in _session_storage:
        await ctx.warning(
            f"No session found for ID: {session_id}, creating new session"
        )
        _session_storage[session_id] = {
            "session_id": session_id,
            "session_name": "Auto-created",
            "start_time": _get_current_time(),
            "client_id": ctx.client_id or "Unknown",
            "request_count": 0,
            "last_activity": _get_current_time(),
            "activities": [],
            "session_data": {},
        }

    session_data = _session_storage[session_id]

    # Update session activity
    session_data["request_count"] += 1
    session_data["last_activity"] = _get_current_time()
    session_data["activities"].append(
        {
            "timestamp": _get_current_time(),
            "action": f"data_update",
            "request_id": ctx.request_id,
            "details": f"Updated key '{key}'",
        }
    )

    # Store the data
    old_value = session_data["session_data"].get(key)
    session_data["session_data"][key] = value

    await ctx.debug(f"Updated session data: {key} = {value}")

    return {
        "status": "updated",
        "session_id": session_id,
        "key": key,
        "old_value": old_value,
        "new_value": value,
        "request_count": session_data["request_count"],
        "last_activity": session_data["last_activity"],
    }


@mcp.tool()
async def get_session_info(ctx: Context) -> dict:
    """Get information about the current session using session ID.

    Returns:
        Dictionary with comprehensive session information
    """
    session_id = getattr(ctx, "session_id", None) or f"session_{ctx.request_id}"
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} requesting session info")

    if session_id not in _session_storage:
        await ctx.debug(f"No session data found for ID: {session_id}")
        return {
            "session_found": False,
            "session_id": session_id,
            "message": "No session tracker started. Use start_session_tracker first.",
            "active_sessions": list(_session_storage.keys()),
        }

    session_data = _session_storage[session_id]

    # Update activity
    session_data["request_count"] += 1
    session_data["last_activity"] = _get_current_time()
    session_data["activities"].append(
        {
            "timestamp": _get_current_time(),
            "action": "info_request",
            "request_id": ctx.request_id,
        }
    )

    await ctx.debug(f"Retrieved session info for: {session_data['session_name']}")

    return {
        "session_found": True,
        "session_id": session_id,
        "session_name": session_data["session_name"],
        "start_time": session_data["start_time"],
        "client_id": session_data["client_id"],
        "request_count": session_data["request_count"],
        "last_activity": session_data["last_activity"],
        "session_data_keys": list(session_data["session_data"].keys()),
        "session_data": session_data["session_data"],
        "recent_activities": session_data["activities"][-5:],  # Last 5 activities
        "total_activities": len(session_data["activities"]),
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

    if not _session_storage:
        await ctx.debug("No active sessions found")
        return {
            "active_session_count": 0,
            "sessions": [],
            "message": "No active sessions",
        }

    # Build session summary
    sessions_summary = []
    for session_id, session_data in _session_storage.items():
        summary = {
            "session_id": session_id,
            "session_name": session_data["session_name"],
            "start_time": session_data["start_time"],
            "client_id": session_data["client_id"],
            "request_count": session_data["request_count"],
            "last_activity": session_data["last_activity"],
            "data_keys": list(session_data["session_data"].keys()),
            "data_count": len(session_data["session_data"]),
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

    if session_id not in _session_storage:
        await ctx.warning(f"No session found for ID: {session_id}")
        return {
            "status": "not_found",
            "session_id": session_id,
            "message": "No session data to clear",
        }

    session_data = _session_storage[session_id]
    data_keys_cleared = list(session_data["session_data"].keys())
    data_count_cleared = len(session_data["session_data"])

    # Clear session data but keep session metadata
    session_data["session_data"] = {}
    session_data["request_count"] += 1
    session_data["last_activity"] = _get_current_time()
    session_data["activities"].append(
        {
            "timestamp": _get_current_time(),
            "action": "data_cleared",
            "request_id": ctx.request_id,
            "details": f"Cleared {data_count_cleared} data items",
        }
    )

    await ctx.info(
        f"Cleared {data_count_cleared} items from session '{session_data['session_name']}'"
    )

    return {
        "status": "cleared",
        "session_id": session_id,
        "session_name": session_data["session_name"],
        "data_keys_cleared": data_keys_cleared,
        "items_cleared": data_count_cleared,
        "request_count": session_data["request_count"],
    }


@mcp.tool()
async def complete_ftl_mission(ctx: Context) -> dict:
    """Complete the current FTL mission and clear it from context state.

    Returns:
        Dictionary with completion summary
    """
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} completing FTL mission")

    # Retrieve current mission
    current_mission = ctx.get_state("current_mission")
    if not current_mission:
        await ctx.warning("No active mission to complete")
        return {"error": "No active mission to complete"}

    # Update mission history
    mission_history = ctx.get_state("mission_history") or []

    # Create completion summary
    completion_summary = {
        "mission_name": current_mission["name"],
        "destination": current_mission["destination"],
        "completion_time": _get_current_time(),
        "total_distance": current_mission["distance_traveled"],
        "final_fuel_level": current_mission["fuel_level"],
        "total_alerts": len(current_mission["alerts"]),
        "mission_duration": "Calculated from start_time",  # Could calculate actual duration
        "status": "completed",
    }

    # Clear current mission from state but keep history
    ctx.set_state("current_mission", None)
    ctx.set_state("last_completed_mission", completion_summary)

    await ctx.info(f"Mission '{current_mission['name']}' completed successfully")

    return completion_summary


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
            elif isinstance(value, dict) and key not in parsed_inventory["groups"]:
                # Process top-level groups that weren't already processed as children of 'all'
                process_group(key, value)

        # Calculate totals
        parsed_inventory["total_hosts"] = len(parsed_inventory["hosts"])
        parsed_inventory["total_groups"] = len(parsed_inventory["groups"])

        # Store in both context state and fallback storage
        ctx.set_state("ansible_inventory", parsed_inventory)
        ctx.set_state("inventory_history", [inventory_path])

        # Fallback storage
        _inventory_storage["ansible_inventory"] = parsed_inventory
        _inventory_storage["inventory_history"] = [inventory_path]

        # Debug: Verify state was stored
        stored_inventory = ctx.get_state("ansible_inventory")
        if stored_inventory:
            await ctx.info(
                f"✅ Context state verified: {stored_inventory['total_hosts']} hosts stored"
            )
        else:
            await ctx.warning("⚠️ Context state not verified, using fallback storage")

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

    inventory = ctx.get_state("ansible_inventory")
    history = ctx.get_state("inventory_history") or []

    # Fallback to in-memory storage if context state is empty
    if not inventory:
        inventory = _inventory_storage["ansible_inventory"]
        history = _inventory_storage["inventory_history"]
        if inventory:
            await ctx.info("Using fallback storage for inventory data")

    # Debug: Log what we found in state
    await ctx.debug(f"Found inventory in state: {inventory is not None}")
    if inventory:
        await ctx.debug(f"Inventory has {len(inventory.get('hosts', {}))} hosts")

    if not inventory:
        await ctx.debug("No inventory loaded in context state")
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

    inventory = ctx.get_state("ansible_inventory")

    # Fallback to in-memory storage if context state is empty
    if not inventory:
        inventory = _inventory_storage["ansible_inventory"]
        if inventory:
            await ctx.info("Using fallback storage for hosts query")

    if not inventory:
        await ctx.warning("No inventory loaded in context state or fallback storage")
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

    inventory = ctx.get_state("ansible_inventory")

    # Fallback to in-memory storage if context state is empty
    if not inventory:
        inventory = _inventory_storage["ansible_inventory"]
        if inventory:
            await ctx.info("Using fallback storage for groups query")

    if not inventory:
        await ctx.warning("No inventory loaded in context state or fallback storage")
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

    # Retrieve inventory from context state
    inventory = ctx.get_state("ansible_inventory")

    # Fallback to in-memory storage if context state is empty
    if not inventory:
        inventory = _inventory_storage["ansible_inventory"]
        if inventory:
            await ctx.info("Using fallback storage for save operation")

    if not inventory:
        await ctx.warning("No inventory found in context state or fallback storage")
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


def main():
    """Run the FTL MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
