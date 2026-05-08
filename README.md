<div align="center">

# Agent Delegation MCP

**MCP server for agent delegation mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-agent-delegation-mcp)](https://pypi.org/project/meok-agent-delegation-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Agent Delegation MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `create_task` | Create a new delegatable task. Required capabilities as comma-separated string. |
| `delegate_task` | Assign a pending task to a specific agent. |
| `get_task_status` | Check the current status and progress of a task. |
| `list_available_agents` | List all registered agents and their capabilities. Optionally filter by required |
| `complete_task` | Mark a task as complete with results, or as failed with error details. |

## Installation

```bash
pip install meok-agent-delegation-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "agent-delegation": {
      "command": "python",
      "args": ["-m", "meok_agent_delegation_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 5 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
