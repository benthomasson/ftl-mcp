
# FTL MCP

An MCP (Model Context Protocol) server for faster-than-light automation, built with Python and FastMCP.

## Features

### Tools
- **get_current_time()** - Get the current timestamp in ISO format
- **calculate_speed(distance, time)** - Calculate speed and determine if it's faster than light
- **list_directory(path)** - List directory contents with detailed metadata

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
│   └── tools.py             # Core business logic functions
├── tests/
│   ├── test_tools.py        # Tests for MCP tools
│   └── test_resources.py    # Tests for MCP resources
├── pyproject.toml           # Project configuration
├── CLAUDE.md               # Development guidance
└── README.md               # This file
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
```

## Requirements

- Python 3.8+
- FastMCP
- MCP
- Pydantic

## License

MIT
