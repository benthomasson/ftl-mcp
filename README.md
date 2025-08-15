
# FTL MCP

An MCP (Model Context Protocol) server for faster-than-light automation, built with Python and FastMCP.

## Features

### Tools

#### Core Tools
- **get_current_time()** - Get the current timestamp in ISO format
- **calculate_speed(distance, time)** - Calculate speed and determine if it's faster than light
- **list_directory(path)** - List directory contents with detailed metadata
- **get_context_info()** - Get FastMCP context information (client ID, request ID, etc.)

#### Session Management
- **start_session_tracker(session_name)** - Initialize session tracking using FastMCP session ID
- **update_session_data(key, value)** - Store session-specific key-value data
- **get_session_info()** - Retrieve current session information and activity log
- **list_active_sessions()** - List all active sessions being tracked
- **clear_session_data()** - Clear session data while preserving session metadata

#### FTL Mission Control (State Management Examples)
- **start_ftl_mission(mission_name, destination)** - Start a mission with state tracking
- **update_ftl_mission(status, fuel_consumed, distance, alert)** - Update mission state
- **get_ftl_mission_status()** - Get current mission status from state
- **complete_ftl_mission()** - Complete and clear mission from state

#### Ansible Inventory Management
- **load_inventory(inventory_path)** - Load Ansible YAML inventory into context state
- **save_inventory(output_path)** - Save current inventory data to YAML file
- **get_inventory_status()** - Get current inventory loading status
- **get_inventory_hosts(group_name)** - Get hosts (all or filtered by group)
- **get_inventory_groups()** - List all inventory groups with metadata

### Resources
- **file://{path}** - Read file contents from any path
- **env://** - Access environment variables

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd ftl-mcp

# Activate virtual environment
source ~/venv/ftl/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

## Usage

### Running the MCP Server

```bash
# Using the command line script
ftl-mcp

# Or run directly
python -m ftl_mcp.server
```

### Development

```bash
# Run tests
pytest -v

# Code formatting
black src/ tests/
isort src/ tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/
```

## Project Structure

```
ftl-mcp/
├── src/ftl_mcp/
│   ├── __init__.py          # Package initialization
│   ├── server.py            # FastMCP server with decorated endpoints
│   ├── state.py             # StateManager with Pydantic models
│   └── tools.py             # Core business logic functions
├── tests/
│   ├── test_tools.py        # Tests for MCP tools
│   ├── test_resources.py    # Tests for MCP resources
│   └── test_state.py        # Tests for StateManager and Pydantic models
├── pyproject.toml           # Project configuration
├── CLAUDE.md               # Development guidance
├── PROMPTS.md              # Conversation history
└── README.md               # This file
```

## Session ID Usage

The FTL MCP server demonstrates advanced usage of FastMCP session IDs for tracking and managing session-specific data:

### Session ID Access
```python
@mcp.tool()
async def example_with_session_id(ctx: Context) -> dict:
    # Get session ID from FastMCP context
    session_id = getattr(ctx, 'session_id', None) or f"session_{ctx.request_id}"
    
    # Use session ID for data isolation
    if session_id not in session_storage:
        session_storage[session_id] = {}
    
    return {"session_id": session_id}
```

### Key Features Demonstrated
- **Session Isolation**: Each client session gets its own data storage
- **Activity Tracking**: Log all activities with timestamps and request IDs  
- **Data Persistence**: Session data persists across multiple tool calls
- **Session Management**: Start, update, query, and clear session-specific data
- **Multi-Session Support**: Track multiple concurrent sessions

### Example Session Usage
```python
# Start a session tracker
await session.call_tool("start_session_tracker", {"session_name": "My Session"})

# Store session-specific data  
await session.call_tool("update_session_data", {"key": "user_pref", "value": "dark_mode"})

# Retrieve session information
result = await session.call_tool("get_session_info", {})
# Returns: session data, activity log, request counts, etc.

# List all active sessions
await session.call_tool("list_active_sessions", {})
```

## Example Usage

Once the server is running, you can use the MCP tools through any MCP-compatible client:

```python
# Calculate if a speed is faster than light
calculate_speed(1000000, 0.001)  # Very fast!
# Returns: {"is_faster_than_light": true, ...}

# List current directory
list_directory(".")
# Returns: {"path": "/current/path", "items": [...]}

# Read a file
# Access via resource: file://path/to/file.txt

# Ansible inventory management
load_inventory("inventory.yml")
get_inventory_hosts("webservers") 
save_inventory("output.yml")
```

## Requirements

- Python 3.8+
- FastMCP
- MCP
- Pydantic

## License

MIT
