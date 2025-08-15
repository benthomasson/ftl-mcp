# MCP Tool Interfaces for Ansible Modules with faster_than_light

## Project Overview

Create MCP tool interfaces for Ansible modules using faster_than_light as the execution backend. This will combine the state-of-the-art MCP tooling with high-performance async execution to create a comprehensive automation platform.

## Architecture Vision

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

## Implementation Phases

### Phase 1: Core Infrastructure Setup

#### 1.1 faster_than_light Integration
- **Goal**: Set up faster_than_light as execution backend
- **Tasks**:
  - Import and configure faster_than_light execution engine
  - Create async module execution wrapper
  - Handle SSH gate management for remote hosts
  - Set up error handling and logging integration

#### 1.2 Module Discovery System
- **Goal**: Dynamically discover and register Ansible modules
- **Tasks**:
  - Scan available Ansible modules from standard paths
  - Parse module documentation for parameter schemas
  - Create dynamic MCP tool registration system
  - Generate tool schemas from module metadata

### Phase 2: Core MCP Tool Implementation

#### 2.1 Generic Module Execution Tool
- **Tool**: `ansible_module(module_name, args, hosts)`
- **Purpose**: Execute any Ansible module via faster_than_light
- **Features**:
  - Dynamic module loading and execution
  - Host targeting (single host, list, or group)
  - Structured result format with performance metrics
  - Error handling and detailed logging

#### 2.2 Common Module-Specific Tools
Create dedicated tools for frequently used modules:

- **`ansible_setup(hosts)`** - Gather facts from hosts
- **`ansible_command(cmd, hosts)`** - Execute shell commands
- **`ansible_copy(src, dest, hosts)`** - Copy files to hosts
- **`ansible_template(src, dest, vars, hosts)`** - Template files
- **`ansible_service(name, state, hosts)`** - Manage services
- **`ansible_package(name, state, hosts)`** - Manage packages

### Phase 3: Advanced Integration Features

#### 3.1 Inventory Integration
- **Goal**: Seamless integration with existing inventory tools
- **Features**:
  - Use loaded inventory from existing MCP inventory tools
  - Support host group targeting (e.g., "webservers", "databases")
  - Session-based host filtering and management
  - Automatic host resolution from group names

#### 3.2 Performance Monitoring
- **Goal**: Comprehensive execution monitoring and metrics
- **Features**:
  - Execution time tracking per module and host
  - Success/failure statistics and reporting
  - faster_than_light performance metrics integration
  - Historical performance trending

#### 3.3 State Management Enhancement
- **Goal**: Track and manage execution state and history
- **Features**:
  - Module execution history in StateManager
  - Execution results storage and retrieval
  - Execution status queries and monitoring
  - Session-based execution grouping

### Phase 4: Advanced Automation Features

#### 4.1 Playbook-like Orchestration
- **Tool**: `ansible_sequence(steps, hosts)`
- **Purpose**: Execute multiple modules in sequence
- **Features**:
  - Multi-step automation workflows
  - Conditional execution based on previous results
  - Error handling and rollback capabilities

#### 4.2 Parallel Execution Management
- **Tool**: `ansible_parallel(modules, hosts)`
- **Purpose**: Execute multiple modules concurrently
- **Features**:
  - Concurrent execution across hosts
  - Resource management and throttling
  - Dependency management between tasks

## Technical Implementation Details

### Integration Points

#### faster_than_light Usage
```python
# Example integration pattern
import faster_than_light as ftl

async def execute_ansible_module(module_name, args, hosts):
    # Use ftl execution engine
    results = await ftl.execute_module(
        module=module_name,
        args=args,
        inventory=hosts,
        async_execution=True
    )
    return process_results(results)
```

#### MCP Tool Pattern
```python
@mcp.tool()
async def ansible_setup(hosts: List[str], ctx: Context) -> dict:
    """Gather facts from specified hosts using Ansible setup module."""
    
    # Resolve hosts from inventory if needed
    target_hosts = resolve_hosts(hosts)
    
    # Execute via faster_than_light
    results = await execute_ansible_module(
        module_name="setup",
        args={},
        hosts=target_hosts
    )
    
    # Store results in state
    store_execution_results(ctx, "setup", results)
    
    return format_results(results)
```

### Data Flow

1. **MCP Client** sends tool request with module and parameters
2. **FTL MCP Server** validates parameters and resolves hosts
3. **StateManager** tracks execution start and session context
4. **faster_than_light** executes module on target hosts asynchronously
5. **Results** are processed, stored, and returned to client
6. **Performance metrics** are captured and stored

### Error Handling Strategy

- **Module Errors**: Capture and format Ansible module errors
- **Connection Errors**: Handle SSH and network failures gracefully
- **Performance Issues**: Monitor and alert on slow executions
- **State Consistency**: Ensure state updates are atomic

### Performance Considerations

- **Async Execution**: Leverage faster_than_light's async capabilities
- **Connection Pooling**: Use SSH gates for efficient remote connections
- **Result Caching**: Cache module results where appropriate
- **Parallel Execution**: Execute across multiple hosts concurrently

## Testing Strategy

### Unit Tests
- Test individual MCP tools with mocked faster_than_light
- Validate parameter parsing and validation
- Test error handling scenarios

### Integration Tests
- Test with real faster_than_light execution
- Validate inventory integration
- Test state management and persistence

### Performance Tests
- Benchmark against native Ansible execution
- Test scalability with large host counts
- Validate performance improvements

## Success Metrics

1. **Functionality**: All common Ansible modules accessible via MCP tools
2. **Performance**: Demonstrate faster_than_light performance benefits
3. **Usability**: Intuitive MCP interface for automation tasks
4. **Reliability**: Robust error handling and state management
5. **Scalability**: Efficient execution across large host inventories

## Future Enhancements

- **Module Development**: Custom FTL-optimized modules
- **Web Interface**: Optional web UI for automation management
- **Integration APIs**: RESTful APIs for external tool integration
- **Advanced Workflows**: Complex automation orchestration
- **Multi-Environment**: Support for multiple inventory environments

---

This plan creates a comprehensive automation platform that combines the best of MCP tooling with high-performance execution, providing a modern alternative to traditional automation tools while maintaining compatibility and ease of use.