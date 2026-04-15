# Agent Delegation MCP Server

> By [MEOK AI Labs](https://meok.ai) — Create and delegate tasks to specialized agents with capability-based matching

## Installation

```bash
pip install agent-delegation-mcp
```

## Usage

```bash
# Run standalone
python server.py

# Or via MCP
mcp install agent-delegation-mcp
```

## Tools

### `create_task`
Create a new delegatable task with priority and required capabilities. Returns compatible agents.

**Parameters:**
- `title` (str): Task title
- `description` (str): Task description
- `priority` (str): Priority level — 'critical', 'high', 'medium', 'low'
- `required_capabilities` (str): Comma-separated capabilities (e.g., 'code_generation,testing')
- `timeout_seconds` (int): Task timeout (default 3600)

### `delegate_task`
Assign a pending task to a specific agent. Validates capability match and agent capacity.

**Parameters:**
- `task_id` (str): Task identifier
- `agent_id` (str): Agent to assign to

### `get_task_status`
Check the current status and progress of a task.

**Parameters:**
- `task_id` (str): Task identifier
- `include_history` (bool): Include full event history

### `list_available_agents`
List all registered agents and their capabilities. Optionally filter by required capability.

**Parameters:**
- `capability_filter` (str): Comma-separated capabilities to filter by

### `complete_task`
Mark a task as complete with results, or as failed with error details.

**Parameters:**
- `task_id` (str): Task identifier
- `result` (str): Result text or error message
- `success` (bool): Whether task succeeded (default True)

## Authentication

Free tier: 15 calls/day. Upgrade at [meok.ai/pricing](https://meok.ai/pricing) for unlimited access.

## License

MIT — MEOK AI Labs
