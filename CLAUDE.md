# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an advanced MCP (Model Context Protocol) server for high-performance automation, combining MCP tooling with faster_than_light execution. The project demonstrates comprehensive automation capabilities with Infrastructure as Code workflows.

## Current State

- **Repository Status**: Production-ready automation platform with 46 passing tests
- **Structure**: Python package in `src/ftl_mcp/` with comprehensive test coverage
- **Technology Stack**: Python 3.8+, FastMCP, faster_than_light, ftl_modules, Pydantic, PyYAML
- **Build System**: Hatchling (configured in pyproject.toml)
- **Testing Framework**: pytest with asyncio support

## Development Commands

**Important**: Always activate the virtual environment before running any Python commands:
```bash
source ~/venv/ftl/bin/activate
```

```bash
# Install dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Run the MCP server
ftl-mcp

# Or run directly
python -m ftl_mcp.server

# Code formatting
black src/ tests/
isort src/ tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/

# Run all tests (46 tests)
pytest -v

# Run specific test suites
pytest tests/test_ansible_integration.py -v
pytest tests/test_playbook_generation.py -v
```

## Architecture Overview

The server implements a 3-layer architecture:

```
MCP Client → FTL MCP Server → faster_than_light Execution Engine
                ↓
           StateManager (Persistent State)
```

### Key Components

1. **MCP Server Layer** (`server.py`): FastMCP-based tools and resources
2. **Integration Layer** (`ftl_integration.py`): faster_than_light execution wrapper
3. **State Management** (`state.py`): Pydantic models with persistent storage
4. **Core Tools** (`tools.py`): Business logic functions

## Major Features

### 1. Ansible Automation (faster_than_light powered)
- **ansible_module()**: Execute any Ansible module with 2-10x performance
- **ansible_setup()**: Gather system facts from hosts
- **ansible_command()**: Execute shell commands remotely
- **ansible_copy()**: Copy files to target hosts
- **close_ansible_connections()**: Clean up SSH connections

### 2. Infrastructure as Code
- **Automatic task logging**: All executed operations are recorded
- **get_playbook_tasks()**: View recorded tasks with statistics
- **generate_playbook()**: Convert tasks to Ansible playbook YAML
- **clear_playbook_tasks()**: Clear task history

### 3. Inventory Management
- **load_inventory()**: Parse Ansible YAML inventory files
- **save_inventory()**: Export inventory to YAML
- **get_inventory_hosts()**: Query hosts by group
- **get_inventory_groups()**: List all inventory groups

### 4. Session Management
- **start_session_tracker()**: Initialize session tracking
- **update_session_data()**: Store session-specific data
- **get_session_info()**: Retrieve session information
- **list_active_sessions()**: View all active sessions

### 5. Core Tools
- **get_context_info()**: FastMCP context information

## Package Structure

```
src/ftl_mcp/
├── __init__.py              # Package initialization
├── server.py                # Main MCP server (FastMCP tools/resources)
├── state.py                 # StateManager with Pydantic models
├── tools.py                 # Core business logic functions
└── ftl_integration.py       # faster_than_light integration layer
```

## Testing Structure

```
tests/
├── test_tools.py                # Core tool functionality
├── test_resources.py            # MCP resource testing
├── test_state.py                # StateManager and Pydantic models
├── test_server_integration.py   # MCP server integration
├── test_ansible_integration.py  # Ansible automation workflow
└── test_playbook_generation.py  # Infrastructure as Code workflow
```

## FastMCP Usage Patterns

The server demonstrates advanced FastMCP patterns:

### Tool Definition
```python
@mcp.tool()
async def ansible_module(
    module_name: str,
    hosts: str,
    module_args: dict = None,
    ctx: Context = None
) -> dict:
    """Execute Ansible module with faster_than_light."""
    # Implementation with context logging
```

### Resource Definition
```python
@mcp.resource("file://{path}")
async def read_file(path: str, ctx: Context) -> str:
    """Read file contents with context logging."""
    # Implementation with error handling
```

### Context Usage
- **ctx.info()**: Information logging
- **ctx.debug()**: Debug logging  
- **ctx.error()**: Error logging
- **ctx.request_id**: Unique request identifier
- **ctx.client_id**: Client identification

## State Management

Uses StateManager with Pydantic models for type safety:

### Models
- **SessionData**: Session tracking with activities
- **SessionActivity**: Individual session actions
- **InventoryData**: Ansible inventory structure
- **InventoryHost/Group**: Inventory components

### Storage
- **Sessions**: `state_manager.set_session(id, data)`
- **Generic**: `state_manager.set_generic(key, value)`
- **Inventory**: `_inventory_storage` (in-memory dict)

## faster_than_light Integration

### Execution Flow
1. MCP tool receives request
2. FTLExecutor discovers ftl_modules package location
3. faster_than_light executes modules from ftl_modules directory
4. SSH gates manage connections
5. Results returned with performance metrics
6. TaskLogger records for playbook generation

### Key Classes
- **FTLExecutor**: Main execution coordinator
- **TaskLogger**: Records tasks for Infrastructure as Code
- **FTLExecutionError**: Execution error handling
- **get_ftl_modules_path()**: Dynamically discovers ftl_modules package location

## Development Guidelines

### Adding New Tools
1. Define business logic in appropriate module
2. Add MCP tool decorator in `server.py`
3. Include comprehensive error handling
4. Add context logging (info/debug/error)
5. Write unit and integration tests
6. Update documentation

### Error Handling Pattern
```python
try:
    result = await execute_operation()
    await ctx.info("Operation successful")
    return result
except Exception as e:
    await ctx.error(f"Operation failed: {str(e)}")
    return {"error": f"Operation failed: {str(e)}"}
```

### Testing Pattern
```python
@pytest.mark.asyncio
async def test_tool_functionality():
    from src.ftl_mcp.server import mcp
    
    async with Client(mcp) as client:
        result = await client.call_tool("tool_name", {"param": "value"})
        assert result.data["status"] == "success"
```

## File References

- **PLAN.md**: Comprehensive implementation roadmap
- **PROMPTS.md**: Complete conversation history
- **inventory.yml**: Example Ansible inventory
- **pyproject.toml**: Project configuration with all dependencies

## Important Notes

1. **Virtual Environment**: Always activate `~/venv/ftl/bin/activate` before commands
2. **Test Coverage**: 46 comprehensive tests cover all functionality
3. **Performance**: 2-10x faster than standard Ansible via faster_than_light
4. **Infrastructure as Code**: Automatic playbook generation from executed tasks
5. **State Persistence**: Uses StateManager, not FastMCP context state
6. **Error Handling**: Comprehensive error handling with context logging
7. **SSH Management**: Automatic connection pooling and cleanup

This is a production-ready automation platform demonstrating advanced MCP capabilities with high-performance execution and Infrastructure as Code workflows.