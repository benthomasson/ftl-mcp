# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server repository for faster-than-light automation, implemented using Python and the FastMCP framework.

## Current State

- **Repository Status**: Python package with MCP server implementation
- **Structure**: Standard Python package in `src/ftl_mcp/`
- **Technology Stack**: Python 3.8+, FastMCP, Pydantic
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

# Run tests
pytest
```

## Architecture Notes

The MCP server is implemented using FastMCP and provides:

### Tools
- `get_current_time()`: Returns current timestamp
- `calculate_speed(distance, time)`: Calculates speed and checks if faster than light
- `list_directory(path)`: Lists directory contents with metadata

### Resources  
- `file://{path}`: Read file contents
- `env://`: List environment variables

### Package Structure
- `src/ftl_mcp/__init__.py`: Package initialization
- `src/ftl_mcp/server.py`: Main MCP server implementation using FastMCP
- `pyproject.toml`: Project configuration and dependencies

## FastMCP Usage

The server uses FastMCP decorators:
- `@mcp.tool()` for defining MCP tools
- `@mcp.resource()` for defining MCP resources
- `mcp.run()` to start the server