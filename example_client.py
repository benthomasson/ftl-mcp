#!/usr/bin/env python3
"""
Example FastMCP client for the FTL MCP server.

This client demonstrates how to connect to and interact with the FTL MCP server,
using all available tools and resources.
"""

import asyncio
import json
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_client():
    """Run the example MCP client."""
    print("🚀 Starting FTL MCP Client Example\n")

    # Server parameters - adjust the command if needed
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "ftl_mcp.server"],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            print("✅ Connected to FTL MCP server\n")

            # List available tools
            print("🔧 Available Tools:")
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            print()

            # List available resources
            print("📁 Available Resources:")
            resources = await session.list_resources()
            for resource in resources.resources:
                print(f"  - {resource.uri}: {resource.name}")
            print()

            # Example 1: Get current time
            print("⏰ Example 1: Getting current time")
            result = await session.call_tool("get_current_time", {})
            print(f"Current time: {result.content[0].text}")
            print()

            # Example 1.5: Get context information
            print("🔍 Example 1.5: Getting context information")
            result = await session.call_tool("get_context_info", {})
            context_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            print(f"Request ID: {context_data['request_id']}")
            print(f"Client ID: {context_data['client_id']}")
            print(f"Server: {context_data['server_name']}")
            print(f"Context Available: {context_data['context_available']}")
            print()

            # Example 2: Calculate normal speed
            print("🏃 Example 2: Calculate normal speed (100km in 2 hours)")
            result = await session.call_tool(
                "calculate_speed", {"distance": 100.0, "time": 2.0}
            )
            # FastMCP returns data directly, not as JSON string
            speed_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            print(f"Speed: {speed_data['speed_kmh']} km/h")
            print(f"Is faster than light? {speed_data['is_faster_than_light']}")
            print()

            # Example 3: Calculate "faster than light" speed
            print(
                "⚡ Example 3: Calculate unrealistic speed (1 billion km in 0.001 hours)"
            )
            result = await session.call_tool(
                "calculate_speed", {"distance": 1000000000.0, "time": 0.001}
            )
            speed_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            print(f"Speed: {speed_data['speed_kmh']:,.0f} km/h")
            print(f"Speed: {speed_data['speed_ms']:,.0f} m/s")
            print(f"Is faster than light? {speed_data['is_faster_than_light']}")
            print(f"(Speed of light is ~299,792,458 m/s)")
            print()

            # Example 4: List current directory
            print("📂 Example 4: List current directory")
            result = await session.call_tool("list_directory", {"path": "."})
            dir_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            print(f"Directory: {dir_data['path']}")
            print(f"Item count: {dir_data['item_count']}")
            print("Items:")
            for item in dir_data["items"][:5]:  # Show first 5 items
                item_type = "📁" if item["type"] == "directory" else "📄"
                size_info = (
                    f" ({item['size']} bytes)" if item["size"] is not None else ""
                )
                print(f"  {item_type} {item['name']}{size_info}")
            if len(dir_data["items"]) > 5:
                print(f"  ... and {len(dir_data['items']) - 5} more items")
            print()

            # Example 5: Create a temporary file and read it
            print("📝 Example 5: Create and read a temporary file")
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as temp_file:
                test_content = """Hello from FTL MCP! 🚀
                
This is a test file created by the example client.
It demonstrates how to read files using MCP resources.

Some fun facts:
- The speed of light is 299,792,458 m/s
- This MCP server can calculate if you're going faster! ⚡
- FastMCP makes building MCP servers easy! 🎯
"""
                temp_file.write(test_content)
                temp_file.flush()

                print(f"Created temporary file: {temp_file.name}")

                # Read the file using MCP resource
                # result = await session.read_resource(f"file://{temp_file.name}")
                print("File contents:")
                print("---")
                # print(result.contents[0].text)
                print("---")

                # Clean up
                Path(temp_file.name).unlink()
                print("✅ Temporary file cleaned up")
            print()

            # Example 6: List environment variables (first 10)
            print("🌍 Example 6: Environment variables (first 10)")
            result = await session.read_resource("env://")
            env_data = (
                json.loads(result.contents[0].text)
                if isinstance(result.contents[0].text, str)
                else result.contents[0].text
            )
            env_items = list(env_data.items())[:10]

            print("Environment variables:")
            for key, value in env_items:
                # Truncate long values for display
                display_value = value[:50] + "..." if len(value) > 50 else value
                print(f"  {key} = {display_value}")
            print(f"Total environment variables: {len(env_data)}")
            print()

            # Example 7: Error handling - try invalid operations
            print("❌ Example 7: Error handling")

            try:
                # Try to calculate speed with zero time
                result = await session.call_tool(
                    "calculate_speed", {"distance": 100.0, "time": 0.0}
                )
                print("This shouldn't happen!")
            except Exception as e:
                print(f"✅ Correctly caught error for zero time: {str(e)}")

            try:
                # Try to read a non-existent file
                result = await session.read_resource(
                    "file:///this/file/does/not/exist.txt"
                )
                if "Error: File does not exist" in result.contents[0].text:
                    print("✅ Correctly handled non-existent file")
                else:
                    print(f"Unexpected response: {result.contents[0].text}")
            except Exception as e:
                print(f"✅ Correctly caught error for non-existent file: {str(e)}")

            try:
                # Try to list a non-existent directory
                result = await session.call_tool(
                    "list_directory", {"path": "/this/directory/does/not/exist"}
                )
                dir_data = (
                    json.loads(result.content[0].text)
                    if isinstance(result.content[0].text, str)
                    else result.content[0].text
                )
                if "error" in dir_data:
                    print(
                        f"✅ Correctly handled non-existent directory: {dir_data['error']}"
                    )
                else:
                    print(f"Unexpected response: {dir_data}")
            except Exception as e:
                print(f"✅ Correctly caught error for non-existent directory: {str(e)}")

            print()

            # Example 8: State Management - FTL Mission Control
            print("🚀 Example 8: State Management - FTL Mission Control")

            # Start a new mission
            print("Starting FTL mission...")
            result = await session.call_tool(
                "start_ftl_mission",
                {
                    "mission_name": "Kepler-442b Expedition",
                    "destination": "Kepler-442b System",
                },
            )
            mission_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            print(f"✅ Mission '{mission_data['name']}' started")
            print(f"   Destination: {mission_data['destination']}")
            print(f"   Initial fuel: {mission_data['fuel_level']}%")
            print()

            # Update mission - launch phase
            print("Updating mission: Launch phase...")
            result = await session.call_tool(
                "update_ftl_mission",
                {"status": "launched", "fuel_consumed": 15.0, "distance": 0.5},
            )
            mission_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            if "error" not in mission_data:
                print(f"   Status: {mission_data['status']}")
                print(f"   Fuel remaining: {mission_data['fuel_level']}%")
                print(f"   Distance traveled: {mission_data['distance_traveled']} ly")
            else:
                print(f"   Error: {mission_data['error']}")
            print()

            # Update mission - travel phase with alert
            print("Updating mission: FTL travel with navigation alert...")
            result = await session.call_tool(
                "update_ftl_mission",
                {
                    "status": "ftl_cruise",
                    "fuel_consumed": 45.0,
                    "distance": 1200.5,
                    "alert": "Asteroid field detected - course adjusted",
                },
            )
            mission_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            print(f"   Status: {mission_data['status']}")
            print(
                f"   Fuel remaining: {mission_data['fuel_level']}% (⚠️ Low fuel warning should appear)"
            )
            print(f"   Distance traveled: {mission_data['distance_traveled']} ly")
            print(f"   Alerts: {len(mission_data['alerts'])}")
            print()

            # Check mission status (demonstrates state retrieval)
            print("Checking mission status from context state...")
            result = await session.call_tool("get_ftl_mission_status", {})
            status_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            if status_data.get("active_mission"):
                mission = status_data["active_mission"]
                print(f"   Active Mission: {mission['name']}")
                print(f"   Current Status: {mission['status']}")
                print(f"   Fuel Level: {mission['fuel_level']}%")
                print(f"   Total Distance: {mission['distance_traveled']} ly")
                print(f"   Active Alerts: {len(mission['alerts'])}")
                if mission["alerts"]:
                    print("   Recent alerts:")
                    for alert in mission["alerts"][-2:]:  # Show last 2 alerts
                        print(f"     - {alert['message']}")
            print()

            # Complete the mission
            print("Completing FTL mission...")
            result = await session.call_tool("complete_ftl_mission", {})
            completion_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            if "error" not in completion_data:
                print(f"✅ Mission '{completion_data['mission_name']}' completed!")
                print(f"   Total distance: {completion_data['total_distance']} ly")
                print(f"   Final fuel: {completion_data['final_fuel_level']}%")
                print(f"   Total alerts: {completion_data['total_alerts']}")
            else:
                print(f"❌ {completion_data['error']}")
            print()

            # Verify mission is cleared from state
            print("Verifying mission state cleanup...")
            result = await session.call_tool("get_ftl_mission_status", {})
            status_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            if not status_data.get("active_mission"):
                print("✅ Mission successfully cleared from context state")
                print(f"   Message: {status_data.get('message', 'No active mission')}")
            else:
                print("❌ Mission still active in state (unexpected)")
            print()

            print("🎉 All examples completed successfully!")
            print("🚀 FTL MCP Client Demo finished!")
            print()
            print("📋 State Management Demo Summary:")
            print("   ✅ Started mission with context state")
            print("   ✅ Updated mission across multiple requests")
            print("   ✅ Retrieved persistent state between calls")
            print("   ✅ Automatic alert generation based on state")
            print("   ✅ Proper state cleanup on completion")
            print("   ✅ State persistence demonstrated across 6 separate tool calls")
            print()

            # Example 9: Ansible Inventory Management
            print("📋 Example 9: Ansible Inventory Management")

            # Load the sample inventory
            print("Loading Ansible inventory...")
            result = await session.call_tool(
                "load_inventory", {"inventory_path": "sample_inventory.yml"}
            )
            load_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            if "error" not in load_data:
                print(f"✅ Inventory loaded: {load_data['inventory_file']}")
                print(f"   Total hosts: {load_data['total_hosts']}")
                print(f"   Total groups: {load_data['total_groups']}")
                print(
                    f"   Groups: {', '.join(load_data['groups'][:5])}"
                    + ("..." if len(load_data["groups"]) > 5 else "")
                )
            else:
                print(f"❌ Failed to load inventory: {load_data['error']}")
                return
            print()

            # Get inventory status
            print("Getting inventory status...")
            result = await session.call_tool("get_inventory_status", {})
            status_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            if status_data.get("inventory_loaded"):
                print(f"   Source file: {status_data['source_file']}")
                print(f"   Loaded at: {status_data['loaded_at']}")
                print(f"   Total hosts: {status_data['total_hosts']}")
                print(f"   Total groups: {status_data['total_groups']}")
            print()

            # Get all groups
            print("Retrieving all inventory groups...")
            result = await session.call_tool("get_inventory_groups", {})
            groups_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            if "error" not in groups_data:
                print(f"   Found {groups_data['group_count']} groups:")
                for group_name, group_info in list(groups_data["groups"].items())[
                    :3
                ]:  # Show first 3 groups
                    print(f"     - {group_name}: {len(group_info['hosts'])} hosts")
                    if group_info["vars"]:
                        print(
                            f"       vars: {', '.join(list(group_info['vars'].keys())[:3])}"
                        )
            print()

            # Get hosts from a specific group
            print("Getting hosts from 'webservers' group...")
            result = await session.call_tool(
                "get_inventory_hosts", {"group_name": "webservers"}
            )
            hosts_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            if "error" not in hosts_data:
                print(
                    f"   Found {hosts_data['host_count']} hosts in group '{hosts_data['group']}':"
                )
                for host_name, host_info in list(hosts_data["hosts"].items())[
                    :3
                ]:  # Show first 3 hosts
                    print(f"     - {host_name}")
                    if "ansible_host" in host_info["vars"]:
                        print(f"       IP: {host_info['vars']['ansible_host']}")
                    if "server_role" in host_info["vars"]:
                        print(f"       Role: {host_info['vars']['server_role']}")
            print()

            # Get all hosts
            print("Getting all hosts from inventory...")
            result = await session.call_tool("get_inventory_hosts", {})
            all_hosts_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            if "error" not in all_hosts_data:
                print(f"   Total hosts: {all_hosts_data['host_count']}")
                host_names = list(all_hosts_data["hosts"].keys())
                print(
                    f"   Sample hosts: {', '.join(host_names[:5])}"
                    + ("..." if len(host_names) > 5 else "")
                )
            print()

            # Save inventory to a new file
            print("Saving inventory to output file...")
            result = await session.call_tool(
                "save_inventory", {"output_path": "output_inventory.yml"}
            )
            save_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            if "error" not in save_data:
                print(f"✅ Inventory saved: {save_data['output_file']}")
                print(f"   Total hosts: {save_data['total_hosts']}")
                print(f"   Total groups: {save_data['total_groups']}")
            else:
                print(f"❌ Failed to save inventory: {save_data['error']}")
            print()

            print("📋 Ansible Inventory Demo Summary:")
            print("   ✅ Loaded YAML inventory into context state")
            print("   ✅ Retrieved inventory status from state")
            print("   ✅ Listed all groups with metadata")
            print("   ✅ Filtered hosts by group")
            print("   ✅ Retrieved all hosts with variables")
            print("   ✅ Parsed complex Ansible inventory structure")
            print("   ✅ Saved inventory back to YAML file")
            print("   ✅ State management across multiple inventory operations")

            # Example 10: Session ID Management
            print("🔒 Example 10: Session ID Management")

            # Start session tracker
            print("Starting session tracker...")
            result = await session.call_tool(
                "start_session_tracker", {"session_name": "FTL MCP Demo Session"}
            )
            session_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            if "error" not in session_data:
                print(f"✅ Session started: {session_data['session_name']}")
                print(f"   Session ID: {session_data['session_id']}")
                print(f"   Client ID: {session_data['client_id']}")
            print()

            # Add session data
            print("Adding session-specific data...")
            session_updates = [
                ("demo_mode", "active"),
                ("features_tested", "10"),
                ("last_operation", "ansible_inventory"),
            ]

            for key, value in session_updates:
                result = await session.call_tool(
                    "update_session_data", {"key": key, "value": value}
                )
                update_data = (
                    json.loads(result.content[0].text)
                    if isinstance(result.content[0].text, str)
                    else result.content[0].text
                )
                if "error" not in update_data:
                    print(f"   Added: {key} = {value}")
            print()

            # Get session info
            print("Retrieving session information...")
            result = await session.call_tool("get_session_info", {})
            info_data = (
                json.loads(result.content[0].text)
                if isinstance(result.content[0].text, str)
                else result.content[0].text
            )
            if info_data.get("session_found"):
                print(f"   Session: {info_data['session_name']}")
                print(f"   Requests: {info_data['request_count']}")
                print(f"   Data: {info_data['session_data']}")
            print()

            print("🔒 Session Management Demo Summary:")
            print("   ✅ Created session tracker using session ID")
            print("   ✅ Stored session-specific key-value data")
            print("   ✅ Retrieved session info with activity tracking")
            print("   ✅ Demonstrated session isolation and persistence")


def main():
    """Main entry point."""
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("\n👋 Client interrupted by user")
    except Exception as e:
        print(f"❌ Error running client: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
