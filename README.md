# FTL MCP

An advanced MCP (Model Context Protocol) server for high-performance automation, combining MCP tooling with faster_than_light execution. Built with Python, FastMCP, and faster_than_light.

## Features

### Ansible Automation Tools (faster_than_light powered)
- **ansible_module(module_name, hosts, module_args)** - Execute any Ansible module with high performance
- **ansible_setup(hosts)** - Gather facts from target hosts
- **ansible_command(command, hosts)** - Execute shell commands on remote hosts
- **ansible_copy(src, dest, hosts)** - Copy files to target hosts
- **close_ansible_connections()** - Clean up SSH connections and resources

### Playbook Generation (Infrastructure as Code)
- **get_playbook_tasks()** - View recorded automation tasks with statistics
- **generate_playbook(playbook_name, include_failed)** - Convert tasks to Ansible playbook YAML
- **clear_playbook_tasks()** - Clear task history to start fresh

### Secrets Management (Secure)
- **get_secrets_status()** - View secrets manager status and statistics (safe)
- **check_secret_exists(name)** - Check if a secret exists without exposing values
- **reload_secrets()** - Reload secrets from environment variables and encrypted files

### Core Tools
- **get_context_info()** - Get FastMCP context information (client ID, request ID, etc.)

### Session Management
- **start_session_tracker(session_name)** - Initialize session tracking using FastMCP session ID
- **update_session_data(key, value)** - Store session-specific key-value data
- **get_session_info()** - Retrieve current session information and activity log
- **list_active_sessions()** - List all active sessions being tracked
- **clear_session_data()** - Clear session data while preserving session metadata

### Ansible Inventory Management
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

### Automation Workflow

The FTL MCP server enables powerful automation workflows:

#### 1. Interactive Automation
```python
# Execute Ansible modules interactively
await client.call_tool("ansible_command", {
    "command": "systemctl status nginx",
    "hosts": "webservers"
})

# Copy configuration files
await client.call_tool("ansible_copy", {
    "src": "nginx.conf",
    "dest": "/etc/nginx/nginx.conf", 
    "hosts": "webservers"
})

# Gather system facts
await client.call_tool("ansible_setup", {
    "hosts": "all"
})
```

#### 2. Infrastructure as Code
```python
# View what tasks have been executed
tasks = await client.call_tool("get_playbook_tasks", {})
print(f"Recorded {tasks.data['summary']['total_tasks']} tasks")

# Generate reusable playbook from executed tasks
playbook = await client.call_tool("generate_playbook", {
    "playbook_name": "webserver_setup",
    "include_failed": False
})

# Save the generated YAML to version control
with open("webserver_setup.yml", "w") as f:
    f.write(playbook.data["yaml"])
```

#### 3. Performance Benefits
- **2-10x faster** than standard Ansible execution
- **Async execution** with SSH connection pooling
- **Concurrent operations** across multiple hosts
- **Real-time monitoring** and execution tracking

#### 4. Secure Secrets Management
```bash
# Load secrets via environment variables (RECOMMENDED)
export FTL_SECRET_SSH_USER=myuser
export FTL_SECRET_SSH_PASSWORD=mypassword
export FTL_SECRET_API_KEY=sk-1234567890

# Check secrets status (safe - no values exposed)
await client.call_tool("get_secrets_status", {})

# Check if specific secrets exist
await client.call_tool("check_secret_exists", {"name": "ssh_user"})

# Reload secrets from environment and files (useful after updating external sources)
await client.call_tool("reload_secrets", {})

# Secrets are automatically used in SSH connections
await client.call_tool("ansible_command", {
    "command": "uptime",
    "hosts": "production_servers"  # Uses SSH credentials from secrets
})
```

### Development

```bash
# Activate virtual environment
source ~/venv/ftl/bin/activate

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
│   ├── __init__.py              # Package initialization
│   ├── server.py                # FastMCP server with all MCP tools
│   ├── state.py                 # StateManager with Pydantic models
│   ├── tools.py                 # Core business logic functions
│   └── ftl_integration.py       # faster_than_light integration layer
├── tests/
│   ├── test_tools.py            # Tests for core tools
│   ├── test_resources.py        # Tests for MCP resources
│   ├── test_state.py            # Tests for StateManager and Pydantic models
│   ├── test_server_integration.py  # MCP server integration tests
│   ├── test_ansible_integration.py # Ansible automation tests
│   └── test_playbook_generation.py # Playbook generation tests
├── pyproject.toml               # Project configuration
├── inventory.yml                # Example Ansible inventory
├── PLAN.md                      # Implementation roadmap
├── CLAUDE.md                    # Development guidance
├── PROMPTS.md                   # Conversation history
└── README.md                    # This file
```

## Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   MCP Client        │───▶│   FTL MCP Server     │───▶│  faster_than_light  │
│   (Control Plane)   │    │   (Management Layer) │    │  (Execution Engine) │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │   StateManager       │
                           │   (State & History)  │
                           └──────────────────────┘
```

## Key Features Demonstrated

### State Management
- **Persistent storage** using StateManager with Pydantic models
- **Session isolation** for multiple concurrent users
- **Activity tracking** with timestamps and request IDs
- **Execution history** for automation tasks

### High-Performance Automation
- **faster_than_light integration** for 2-10x performance improvement
- **SSH connection pooling** and gate management
- **Async execution** with concurrent host operations
- **Error handling** and comprehensive logging

### Infrastructure as Code
- **Automatic task logging** for all executed operations
- **Playbook generation** from recorded automation tasks
- **YAML export** for version control and repeatability
- **Task filtering** and optimization

### Example Session Usage
```python
# Start session tracking
await client.call_tool("start_session_tracker", {"session_name": "Production Deploy"})

# Load inventory for targeting
await client.call_tool("load_inventory", {"inventory_path": "production.yml"})

# Execute automation tasks
await client.call_tool("ansible_copy", {
    "src": "app.tar.gz", 
    "dest": "/opt/app/", 
    "hosts": "app_servers"
})

await client.call_tool("ansible_command", {
    "command": "systemctl restart app",
    "hosts": "app_servers"  
})

# Generate playbook from session
playbook = await client.call_tool("generate_playbook", {
    "playbook_name": "production_deploy"
})

# Save for future use
with open("production_deploy.yml", "w") as f:
    f.write(playbook.data["yaml"])
```

## Requirements

- Python 3.8+
- FastMCP
- MCP
- Pydantic
- PyYAML
- faster_than_light
- ftl_modules (automation modules package)
- cryptography (for secrets encryption)
- anyio

## Testing

The project includes comprehensive test coverage:
- **62 tests** covering all functionality
- **Unit tests** for individual components
- **Integration tests** for MCP server tools
- **Ansible execution tests** using faster_than_light test modules
- **Playbook generation tests** for Infrastructure as Code workflows
- **Secrets management tests** for secure credential handling

```bash
# Run all tests
pytest -v

# Run specific test suites
pytest tests/test_ansible_integration.py -v
pytest tests/test_playbook_generation.py -v
```

## Performance

Leverages faster_than_light for significant performance improvements:
- **2-10x faster** execution compared to standard Ansible
- **Async-first architecture** with concurrent operations
- **SSH connection pooling** for efficient remote access
- **Optimized module execution** with minimal overhead

## License

MIT