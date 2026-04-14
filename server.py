#!/usr/bin/env python3
import json, uuid
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("agent-delegation-mcp")
_TASKS: dict = {}
@mcp.tool(name="delegate_task")
async def delegate_task(agent_id: str, task_description: str, priority: str = "medium") -> str:
    tid = str(uuid.uuid4())[:12]
    _TASKS[tid] = {"agent": agent_id, "task": task_description, "priority": priority, "status": "pending"}
    return json.dumps({"task_id": tid, "agent": agent_id, "status": "delegated"})
@mcp.tool(name="task_status")
async def task_status(task_id: str) -> str:
    t = _TASKS.get(task_id)
    return json.dumps(t or {"error": "Task not found"})
@mcp.tool(name="list_pending_tasks")
async def list_pending_tasks(agent_id: str) -> str:
    return json.dumps({"tasks": [t for t in _TASKS.values() if t["agent"] == agent_id and t["status"] == "pending"]})
if __name__ == "__main__":
    mcp.run()
