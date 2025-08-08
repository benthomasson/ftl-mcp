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
            
            # Example 2: Calculate normal speed
            print("🏃 Example 2: Calculate normal speed (100km in 2 hours)")
            result = await session.call_tool("calculate_speed", {
                "distance": 100.0,
                "time": 2.0
            })
            # FastMCP returns data directly, not as JSON string
            speed_data = json.loads(result.content[0].text) if isinstance(result.content[0].text, str) else result.content[0].text
            print(f"Speed: {speed_data['speed_kmh']} km/h")
            print(f"Is faster than light? {speed_data['is_faster_than_light']}")
            print()
            
            # Example 3: Calculate "faster than light" speed
            print("⚡ Example 3: Calculate unrealistic speed (1 billion km in 0.001 hours)")
            result = await session.call_tool("calculate_speed", {
                "distance": 1000000000.0,
                "time": 0.001
            })
            speed_data = json.loads(result.content[0].text) if isinstance(result.content[0].text, str) else result.content[0].text
            print(f"Speed: {speed_data['speed_kmh']:,.0f} km/h")
            print(f"Speed: {speed_data['speed_ms']:,.0f} m/s")
            print(f"Is faster than light? {speed_data['is_faster_than_light']}")
            print(f"(Speed of light is ~299,792,458 m/s)")
            print()
            
            # Example 4: List current directory
            print("📂 Example 4: List current directory")
            result = await session.call_tool("list_directory", {"path": "."})
            dir_data = json.loads(result.content[0].text) if isinstance(result.content[0].text, str) else result.content[0].text
            print(f"Directory: {dir_data['path']}")
            print(f"Item count: {dir_data['item_count']}")
            print("Items:")
            for item in dir_data['items'][:5]:  # Show first 5 items
                item_type = "📁" if item['type'] == 'directory' else "📄"
                size_info = f" ({item['size']} bytes)" if item['size'] is not None else ""
                print(f"  {item_type} {item['name']}{size_info}")
            if len(dir_data['items']) > 5:
                print(f"  ... and {len(dir_data['items']) - 5} more items")
            print()
            
            # Example 5: Create a temporary file and read it
            print("📝 Example 5: Create and read a temporary file")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
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
                result = await session.read_resource(f"file://{temp_file.name}")
                print("File contents:")
                print("---")
                print(result.contents[0].text)
                print("---")
                
                # Clean up
                Path(temp_file.name).unlink()
                print("✅ Temporary file cleaned up")
            print()
            
            # Example 6: List environment variables (first 10)
            print("🌍 Example 6: Environment variables (first 10)")
            result = await session.read_resource("env://")
            env_data = json.loads(result.contents[0].text) if isinstance(result.contents[0].text, str) else result.contents[0].text
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
                result = await session.call_tool("calculate_speed", {
                    "distance": 100.0,
                    "time": 0.0
                })
                print("This shouldn't happen!")
            except Exception as e:
                print(f"✅ Correctly caught error for zero time: {str(e)}")
            
            try:
                # Try to read a non-existent file
                result = await session.read_resource("file:///this/file/does/not/exist.txt")
                if "Error: File does not exist" in result.contents[0].text:
                    print("✅ Correctly handled non-existent file")
                else:
                    print(f"Unexpected response: {result.contents[0].text}")
            except Exception as e:
                print(f"✅ Correctly caught error for non-existent file: {str(e)}")
            
            try:
                # Try to list a non-existent directory
                result = await session.call_tool("list_directory", {
                    "path": "/this/directory/does/not/exist"
                })
                dir_data = json.loads(result.content[0].text) if isinstance(result.content[0].text, str) else result.content[0].text
                if "error" in dir_data:
                    print(f"✅ Correctly handled non-existent directory: {dir_data['error']}")
                else:
                    print(f"Unexpected response: {dir_data}")
            except Exception as e:
                print(f"✅ Correctly caught error for non-existent directory: {str(e)}")
            
            print()
            print("🎉 All examples completed successfully!")
            print("🚀 FTL MCP Client Demo finished!")


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