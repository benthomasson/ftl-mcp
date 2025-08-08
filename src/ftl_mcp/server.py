"""FTL MCP server implementation using fastmcp."""

from fastmcp import FastMCP, Context

from .tools import (
    get_current_time as _get_current_time,
    calculate_speed as _calculate_speed,
    list_directory as _list_directory,
    read_file as _read_file,
    list_environment_variables as _list_environment_variables,
)

# Create the MCP server
mcp = FastMCP("ftl-mcp")


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
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} calculating speed: {distance}km in {time}h")
    
    try:
        result = _calculate_speed(distance, time)
        is_ftl = result.get('is_faster_than_light', False)
        if is_ftl:
            await ctx.warning(f"⚡ FASTER THAN LIGHT detected! Speed: {result['speed_ms']:,.0f} m/s")
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
        "timestamp": _get_current_time()
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
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} starting FTL mission: {mission_name}")
    
    # Initialize mission state
    mission_data = {
        "name": mission_name,
        "destination": destination,
        "status": "planning",
        "start_time": _get_current_time(),
        "fuel_level": 100.0,
        "crew_count": 5,
        "distance_traveled": 0.0,
        "alerts": []
    }
    
    # Store in context state
    ctx.set_state("current_mission", mission_data)
    ctx.set_state("mission_history", [mission_name])
    
    await ctx.info(f"Mission '{mission_name}' initialized in context state")
    return mission_data


@mcp.tool()
async def update_ftl_mission(status: str = None, fuel_consumed: float = 0.0, 
                           distance: float = 0.0, alert: str = None, ctx: Context = None) -> dict:
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
        return {"error": "No active mission. Start a mission first using start_ftl_mission."}
    
    # Update mission data
    if status:
        current_mission["status"] = status
        await ctx.info(f"Mission status updated to: {status}")
    
    if fuel_consumed > 0:
        current_mission["fuel_level"] = max(0.0, current_mission["fuel_level"] - fuel_consumed)
        await ctx.debug(f"Fuel consumed: {fuel_consumed}, remaining: {current_mission['fuel_level']}")
    
    if distance > 0:
        current_mission["distance_traveled"] += distance
        await ctx.debug(f"Distance traveled: +{distance}, total: {current_mission['distance_traveled']}")
    
    if alert:
        current_mission["alerts"].append({
            "timestamp": _get_current_time(),
            "message": alert
        })
        await ctx.warning(f"Mission alert: {alert}")
    
    # Check for critical conditions
    if current_mission["fuel_level"] < 20.0:
        fuel_alert = f"LOW FUEL WARNING: {current_mission['fuel_level']:.1f}% remaining"
        current_mission["alerts"].append({
            "timestamp": _get_current_time(),
            "message": fuel_alert
        })
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
            "message": "No active mission"
        }
    
    await ctx.debug(f"Retrieved mission: {current_mission['name']}")
    
    return {
        "active_mission": current_mission,
        "mission_history": mission_history,
        "state_info": {
            "context_id": ctx.request_id,
            "client_id": ctx.client_id or "Unknown"
        }
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
        "status": "completed"
    }
    
    # Clear current mission from state but keep history
    ctx.set_state("current_mission", None)
    ctx.set_state("last_completed_mission", completion_summary)
    
    await ctx.info(f"Mission '{current_mission['name']}' completed successfully")
    
    return completion_summary


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
    await ctx.info(f"Client {ctx.client_id or 'Unknown'} requested environment variables")
    
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